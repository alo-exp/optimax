# Install a packaged optimax skill locally.
import argparse
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import zipfile

REQUIRED = {
    'SKILL.md', 'agents/openai.yaml',
    'references/calculator.md', 'references/native-modes.md',
    'references/platforms.md', 'references/policy.md',
    'references/parallel-execution.md',
    'scripts/ladder.py', 'scripts/performance.py', 'scripts/session_policy.py',
    'scripts/native_dispatch.py', 'scripts/work_breakdown.py',
}
EXCLUDED = {'tests', 'model-perf', '.git', '__pycache__'}


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
    skill = z.read(files['SKILL.md']).decode('utf-8')
    if not re.match(r'\A---\s*\n(?:(?!---\s*$).*\n)*?name:\s*optimax\s*$', skill, re.MULTILINE):
        raise ValueError('SKILL.md must name optimax')
    for info in files.values():
        with z.open(info) as stream:
            while stream.read(65536): pass
    return files


def _identity(path):
    s = path.lstat()
    return s.st_dev, s.st_ino


def install(archive, dest):
    dest = Path(dest)
    with zipfile.ZipFile(archive) as z:
        files = _manifest(z)
        owned = []
        dest.mkdir()  # Exclusive: never replace a pre-existing destination.
        owned.append((dest, _identity(dest), True))
        try:
            for directory in ('agents', 'references', 'scripts'):
                path = dest / directory
                path.mkdir()
                owned.append((path, _identity(path), True))
            for name, info in sorted(files.items()):
                target = dest / name
                with target.open('xb') as output:
                    owned.append((target, _identity(target), False))
                    with z.open(info) as source:
                        shutil.copyfileobj(source, output)
        except BaseException as exc:
            incomplete = False
            for path, identity, is_dir in reversed(owned):
                try:
                    if _identity(path) != identity:
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
    except (OSError, ValueError, UnicodeError, zipfile.BadZipFile) as exc:
        print(f'installation failed: {exc}', file=sys.stderr)
        return 1
    print(f'Installed optimax to {args.dest}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
