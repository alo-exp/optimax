"""Bounded, read-only discovery of potential instruction conflicts.

Discovery is not a host instruction loader or an authority determination.
"""
import argparse
import errno
import json
import os
from pathlib import Path
import re
import stat
import sys

MAX_FILE = 65536
MAX_TOTAL = 524288
MAX_FINDINGS = 100
MAX_ANCESTORS = 64
PATTERNS = {
    "fixed_helper_model_effort": re.compile(r"(?i)(sub.?agents?|delegat\w*|helpers?|advisors?).{0,100}(model|effort|\bsol\b|\bterra\b|\bopus\b|\bhaiku\b|\bsonnet\b)|(model|effort).{0,100}(sub.?agents?|delegat\w*|helpers?|advisors?)"),
    "delegation_advisor_restrictions": re.compile(r"(?i)(no|never|do not|must not|prohibit|restrict|only).{0,80}(delegat\w*|sub.?agents?|advisors?)|(delegat\w*|sub.?agents?|advisors?).{0,80}(prohibit|restrict|only|must not)"),
    "assessment_storage_performance_policy": re.compile(r"(?i)(assessment|performance|scores?|ledger|csv).{0,80}(must|only|never|prohibit|store|retain|record|disable)|(must|only|never|prohibit).{0,80}(assessment|performance|scores?|ledger|csv)"),
}


def validate_context(context):
    if context is None:
        return {}
    if not isinstance(context, dict) or set(context) - {"cwd", "host_confirmed_loaded", "codex_fallback_names", "codex_max_bytes"}:
        raise ValueError("invalid instruction_context keys or type")
    if "cwd" in context:
        cwd = context["cwd"]
        if not isinstance(cwd, str) or not os.path.isabs(cwd) or Path(cwd).resolve() != Path.cwd().resolve():
            raise ValueError("instruction_context cwd must match the actual working directory")
    for key in ("host_confirmed_loaded", "codex_fallback_names"):
        if key in context and (not isinstance(context[key], list) or len(context[key]) > 32 or any(not isinstance(x, str) or not x or len(x) > 4096 for x in context[key])):
            raise ValueError("invalid instruction_context " + key)
    for name in context.get("codex_fallback_names", []):
        if name in (".", "..") or Path(name).name != name or "/" in name or "\\" in name:
            raise ValueError("fallback names must be file names")
    if "codex_max_bytes" in context and (type(context["codex_max_bytes"]) is not int or not 1 <= context["codex_max_bytes"] <= MAX_TOTAL):
        raise ValueError("invalid codex_max_bytes")
    return context


_SAFE_DIRFD = os.open in os.supports_dir_fd and os.stat in os.supports_dir_fd and os.stat in os.supports_follow_symlinks


class _Disappeared(OSError):
    pass


def _safe_open(path):
    """Open a canonical absolute path without following any path component."""
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    directory = getattr(os, "O_DIRECTORY", 0)
    if not (_SAFE_DIRFD and nofollow and directory and path.is_absolute() and path.anchor == "/"):
        raise NotImplementedError("safe no-follow directory traversal unavailable")
    dirfd = os.open("/", os.O_RDONLY | directory | nofollow)
    try:
        for part in path.parts[1:-1]:
            nextfd = os.open(part, os.O_RDONLY | directory | nofollow, dir_fd=dirfd)
            os.close(dirfd)
            dirfd = nextfd
        metadata = os.stat(path.name, dir_fd=dirfd, follow_symlinks=False)
        if stat.S_ISLNK(metadata.st_mode):
            raise OSError(errno.ELOOP, "symlink candidate")
        try:
            return os.open(path.name, os.O_RDONLY | nofollow | getattr(os, "O_NONBLOCK", 0), dir_fd=dirfd)
        except FileNotFoundError as error:
            raise _Disappeared("candidate disappeared before open") from error
    finally:
        os.close(dirfd)


def _codex_ancestors(cwd, gaps):
    for directory in (cwd, *cwd.parents):
        try:
            marker = (directory / ".git").lstat()
        except FileNotFoundError:
            continue
        except OSError:
            gaps.append("Could not inspect Git root marker; using working directory only.")
            return [cwd]
        if stat.S_ISDIR(marker.st_mode) or stat.S_ISREG(marker.st_mode):
            return list(reversed([cwd, *list(cwd.parents)[:len(cwd.relative_to(directory).parts)]]))
    gaps.append("Git project root unknown; Codex local candidates limited to working directory.")
    return [cwd]

def audit_instructions(platform=None, context=None):
    if platform not in (None, "codex", "claude"):
        raise ValueError("invalid platform")
    context = validate_context(context)
    cwd = Path.cwd().resolve()
    home = Path.home().resolve()
    codex_home = Path(os.environ.get("CODEX_HOME", str(home / ".codex"))).expanduser().resolve()
    platforms = {platform} if platform else {"codex", "claude"}
    gaps = ["Discovered files are current bytes, not proof of instructions loaded in this session; host must review applicability, priority and conversation.",
            "Host instruction inventory, settings, imports and managed instructions may be incomplete; pattern matches are potential conflicts only."]
    if platform is None:
        gaps.append("Host platform was not specified; both conventions are candidates.")
    if "codex" in platforms and ("codex_fallback_names" not in context or "codex_max_bytes" not in context):
        gaps.append("Codex fallback names or instruction size settings are unknown.")
    if "claude" in platforms:
        gaps.append("Claude active files, rules, imports and managed settings are host-dependent and not resolved.")
    ancestors = list(reversed((cwd, *cwd.parents)))
    if len(ancestors) > MAX_ANCESTORS:
        ancestors = ancestors[-MAX_ANCESTORS:]
        gaps.append("Ancestor depth exceeded audit limit.")
    candidates = []
    seen = set()
    def add(path, scope, root):
        key = (str(path), scope.split("_", 1)[0])
        if key not in seen:
            seen.add(key)
            candidates.append((path, scope, root))
    if "codex" in platforms:
        for name in ("AGENTS.override.md", "AGENTS.md", *context.get("codex_fallback_names", [])):
            add(codex_home / name, "codex_global", codex_home)
        codex_ancestors = _codex_ancestors(cwd, gaps)
        if len(codex_ancestors) > MAX_ANCESTORS:
            codex_ancestors = codex_ancestors[-MAX_ANCESTORS:]
            gaps.append("Codex project ancestor depth exceeded audit limit.")
        for directory in codex_ancestors:
            for name in ("AGENTS.override.md", "AGENTS.md", *context.get("codex_fallback_names", [])):
                add(directory / name, "codex_ancestor", directory)
    if "claude" in platforms:
        add(home / ".claude" / "CLAUDE.md", "claude_global", home / ".claude")
        for directory in ancestors:
            for name in ("CLAUDE.md", "CLAUDE.local.md", "AGENTS.md"):
                add(directory / name, "claude_ancestor", directory)
    results, findings = [], []
    remaining = MAX_TOTAL
    for path, scope, root in candidates:
        record = {"path": str(path), "scope": scope, "read_status": "missing"}
        results.append(record)
        try:
            fd = _safe_open(path)
            with os.fdopen(fd, "rb") as stream:
                file_info = os.fstat(stream.fileno())
                if not stat.S_ISREG(file_info.st_mode):
                    record["read_status"] = "not_regular"
                    gaps.append("Skipped non-regular candidate: " + str(path))
                    continue
                host_limit = context.get("codex_max_bytes", MAX_FILE) if scope.startswith("codex_") else MAX_FILE
                cap = min(MAX_FILE, remaining, host_limit)
                data = stream.read(min(cap + 1, remaining))
            remaining -= len(data)
            if cap == 0 or len(data) > cap or file_info.st_size > len(data):
                record["read_status"] = "size_limit"
                gaps.append("Candidate exceeded audit byte limit: " + str(path))
                continue
            content = data.decode("utf-8", errors="strict")
            record["read_status"] = "read"
            for number, line in enumerate(content.splitlines(), 1):
                for category, pattern in PATTERNS.items():
                    if pattern.search(line):
                        if len(findings) < MAX_FINDINGS:
                            findings.append(dict(path=str(path), scope=scope, category=category, line=number, excerpt=line[:240]))
                        elif "Finding limit reached." not in gaps:
                            gaps.append("Finding limit reached.")
        except FileNotFoundError:
            pass
        except NotImplementedError:
            record["read_status"] = "unreviewed"
            if "Safe no-follow directory traversal unavailable; candidates unreviewed." not in gaps:
                gaps.append("Safe no-follow directory traversal unavailable; candidates unreviewed.")
        except (OSError, UnicodeError) as error:
            if isinstance(error, OSError) and error.errno in (errno.ELOOP, errno.ENOTDIR):
                record["read_status"] = "unsafe_symlink"
            else:
                record["read_status"] = "error"
            gaps.append("Could not read candidate " + str(path) + ": " + type(error).__name__)
    return dict(candidates=results, findings=findings, host_confirmed_loaded=list(context.get("host_confirmed_loaded", [])),
                coverage=dict(complete=False, gaps=gaps))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", choices=("codex", "claude"))
    parser.add_argument("--instruction-context", help="JSON host assertions and settings claims")
    args = parser.parse_args(argv)
    try:
        context = json.loads(args.instruction_context) if args.instruction_context is not None else None
        print(json.dumps(audit_instructions(args.platform, context), ensure_ascii=False))
    except (ValueError, TypeError, OSError) as error:
        print("error: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
