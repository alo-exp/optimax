# Install a packaged optimax skill locally.
import argparse
import io
import lzma
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import zipfile
import zlib

REQUIRED = {
    'SKILL.md', 'agents/openai.yaml',
    'references/calculator.md', 'references/native-modes.md',
    'references/platforms.md', 'references/policy.md',
    'references/parallel-execution.md',
    'scripts/ladder.py', 'scripts/performance.py', 'scripts/session_policy.py',
    'scripts/native_dispatch.py', 'scripts/work_breakdown.py',
    'scripts/instruction_audit.py',
}
EXCLUDED = {'tests', 'model-perf', '.git', '__pycache__'}
MAX_MEMBER_BYTES = 1024 * 1024
MAX_TOTAL_BYTES = 8 * 1024 * 1024
READ_CHUNK_BYTES = 64 * 1024


def _stream_member(z, info, budget, output=None):
    """Consume through EOF with bounded reads; check decoded bytes before writing."""
    member_bytes = 0
    try:
        with z.open(info) as stream:
            while True:
                remaining = min(MAX_MEMBER_BYTES - member_bytes, MAX_TOTAL_BYTES - budget[0])
                chunk = stream.read(min(READ_CHUNK_BYTES, remaining + 1))
                if not chunk:
                    break
                member_bytes += len(chunk)
                budget[0] += len(chunk)
                if member_bytes > MAX_MEMBER_BYTES or budget[0] > MAX_TOTAL_BYTES:
                    raise ValueError(f'archive byte limit exceeded: {info.filename}')
                if output is not None:
                    output.write(chunk)
    except (RuntimeError, NotImplementedError) as exc:
        raise ValueError(f'unreadable archive entry {info.filename}: {exc}') from exc

# Reject common YAML implicit non-string scalars in the supported plain subset.
NONSTRING_SCALAR = re.compile(
    r'''(?:[+-]?(?:[0-9][0-9_]*(?::[0-9_]+)*(?:\.[0-9_]*)?(?:[eE][+-]?[0-9]+)?
        |\.[0-9_]+(?:[eE][+-]?[0-9]+)?|0[xX][0-9a-fA-F_]+|0[bB][01_]+|\.inf)
        |\.nan|[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}(?:[Tt \t].*)?)''',
    re.IGNORECASE | re.VERBOSE,
)


# This is the installer's supported single-line plain scalar subset, not a YAML parser.
def _supported_plain_scalar(value):
    return (bool(value)
            and value[0] not in "\"'|>!&*{}[],#%@`"
            and not (value[0] in '-?:' and (len(value) == 1 or value[1] == ' '))
            and not re.search(r':(?: |$)| #', value)
            and value not in ('=', '<<'))


def _supported_header_character(ch):
    code = ord(ch)
    return (code >= 0x20 and not 0x7f <= code <= 0x9f
            and not 0xd800 <= code <= 0xdfff
            and not 0xfdd0 <= code <= 0xfdef
            and code & 0xffff not in (0xfffe, 0xffff)
            and code not in (0x2028, 0x2029))


def _validate_skill_frontmatter(skill, expected_name='optimax'):
    raw_lines = skill.split('\n')
    lines = [line[:-1] if line.endswith('\r') and i < len(raw_lines) - 1 else line
             for i, line in enumerate(raw_lines)]
    if not lines or lines[0] != '---':
        raise ValueError('SKILL.md must start with frontmatter')
    try:
        end = lines.index('---', 1)
    except ValueError:
        raise ValueError('SKILL.md frontmatter must be closed') from None
    fields = {}
    for line in lines[1:end]:
        if not all(_supported_header_character(ch) for ch in line):
            raise ValueError('SKILL.md frontmatter contains unsupported characters')
        match = re.fullmatch(r'(name|description): +(.*)', line)
        if not match or match.group(1) in fields:
            raise ValueError('SKILL.md frontmatter must use unique plain name and description fields')
        fields[match.group(1)] = match.group(2).strip(' ')
    description = fields.get('description', '')
    if (fields.get('name') != expected_name or not _supported_plain_scalar(description)
            or description.casefold() in ('null', 'true', 'false', 'yes', 'no', 'on', 'off', '~')
            or NONSTRING_SCALAR.fullmatch(description)):
        raise ValueError(f'SKILL.md must name {expected_name} and have a nonempty plain description')


def _manifest(z):
    files = {}
    seen = set()
    for info in z.infolist():
        name = info.filename
        path = PurePosixPath(name)
        parts = name.rstrip('/').split('/')
        mode = info.external_attr >> 16
        if (not name or '\\' in name or any(p in ('', '.', '..') for p in parts)
                or path.is_absolute() or parts[0] != 'optimax'
                or stat.S_ISLNK(mode)):
            raise ValueError(f'unsafe archive entry: {name}')
        key = '/'.join(parts)
        if key in seen:
            raise ValueError(f'duplicate archive entry: {name}')
        seen.add(key)
        if len(parts) == 1:
            if not info.is_dir(): raise ValueError('archive root must be a directory')
            continue
        rel = '/'.join(parts[1:])
        if parts[1] in EXCLUDED or '__pycache__' in parts or rel.endswith(('.pyc', '.csv')):
            continue
        if info.is_dir():
            if rel not in ('agents', 'references', 'scripts'):
                raise ValueError(f'unexpected archive directory: {name}')
            continue
        allowed = (rel in ('SKILL.md', 'LICENSE', 'agents/openai.yaml') or
                   len(parts) == 3 and ((parts[1] == 'references' and parts[2].endswith('.md')) or
                                        (parts[1] == 'scripts' and parts[2].endswith('.py'))))
        if not allowed:
            raise ValueError(f'unexpected runtime path: {name}')
        files[rel] = info
    missing = REQUIRED - files.keys()
    if missing: raise ValueError(f'missing required runtime files: {sorted(missing)}')
    if (any(info.file_size > MAX_MEMBER_BYTES for info in files.values())
            or sum(info.file_size for info in files.values()) > MAX_TOTAL_BYTES):
        raise ValueError('archive byte limit exceeded')
    budget = [0]
    skill = io.BytesIO()
    for name, info in files.items():
        _stream_member(z, info, budget, skill if name == 'SKILL.md' else None)
    _validate_skill_frontmatter(skill.getvalue().decode('utf-8'))
    return files


def _identity(path):
    s = path.lstat()
    return s.st_dev, s.st_ino


def install(archive, dest):
    dest = Path(dest)
    with zipfile.ZipFile(archive) as z:
        files = _manifest(z)
        owned = [(dest, None, True)]  # Creation is pending until identity is captured.
        try:
            try:
                dest.mkdir()  # Exclusive: never replace a pre-existing destination.
            except FileExistsError:
                owned.clear()
                raise
            owned[0] = (dest, _identity(dest), True)
            for directory in ('agents', 'references', 'scripts'):
                path = dest / directory
                path.mkdir()
                owned.append((path, _identity(path), True))
            budget = [0]
            for name, info in sorted(files.items()):
                target = dest / name
                with target.open('xb') as output:
                    owned.append((target, _identity(target), False))
                    _stream_member(z, info, budget, output)
        except BaseException as exc:
            incomplete = False
            for path, identity, is_dir in reversed(owned):
                try:
                    if identity is None:
                        path.lstat()  # Existence only; ownership remains unknown.
                        incomplete = True
                    elif _identity(path) != identity:
                        incomplete = True
                    elif is_dir:
                        path.rmdir()
                    else:
                        path.unlink()
                except FileNotFoundError:
                    pass
                except OSError:
                    incomplete = True
            if incomplete:
                raise OSError(f'{exc}; incomplete cleanup at {dest}') from exc
            raise


def main(argv=None):
    parser = argparse.ArgumentParser(description='Install an optimax ZIP locally')
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--dest', type=Path, default=Path.home() / '.codex/skills/optimax')
    args = parser.parse_args(argv)
    try:
        install(args.archive, args.dest)
    except (OSError, ValueError, UnicodeError, zipfile.BadZipFile, zlib.error, lzma.LZMAError) as exc:
        print(f'installation failed: {exc}', file=sys.stderr)
        return 1
    print(f'Installed optimax to {args.dest}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
