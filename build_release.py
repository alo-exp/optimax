#!/usr/bin/env python3
"""Build reproducible, allowlisted Optimax release archives."""
import argparse
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / 'skills' / 'optimax'
FILES = (
    'SKILL.md', 'agents/openai.yaml',
    'references/calculator.md', 'references/native-modes.md',
    'references/platforms.md', 'references/policy.md', 'references/parallel-execution.md',
    'scripts/install_local.py', 'scripts/ladder.py', 'scripts/performance.py',
    'scripts/session_policy.py', 'scripts/native_dispatch.py', 'scripts/work_breakdown.py',
    'scripts/instruction_audit.py',
)
REVIEW_LADDER_FILES = ('SKILL.md', 'agents/openai.yaml', 'references/report-template.md')
MANIFESTS = ('plugin.json', '.codex-plugin/plugin.json', '.claude-plugin/plugin.json')


def read_safe(root, relative):
    path = root / relative
    if any(part.is_symlink() for part in (path, *path.parents) if part != root.parent):
        raise ValueError(f'symlink in release path: {relative}')
    if not path.is_file():
        raise ValueError(f'missing release file: {relative}')
    return path.read_bytes()


def build(output):
    output = Path(output).absolute()
    if output.is_symlink():
        raise ValueError(f'symlink in output path: {output}')
    # Parent aliases are caller path semantics; never follow an output leaf link.
    output = output.parent.resolve() / output.name
    destinations = [output / name for name in ('optimax-skill.zip', 'optimax-plugin.zip')]
    for destination in destinations:
        if destination.is_symlink() or (destination.exists() and not stat.S_ISREG(destination.stat().st_mode)):
            raise ValueError(f'output destination is not a regular file: {destination}')
    runtime = {name: read_safe(RUNTIME, name) for name in FILES}
    if b'name: optimax\n' not in runtime['SKILL.md'].split(b'---', 2)[1]:
        raise ValueError('invalid skill name')
    review_ladder = {'skills/review-ladder/' + name: read_safe(ROOT, 'skills/review-ladder/' + name)
                     for name in REVIEW_LADDER_FILES}
    license_data = read_safe(ROOT, 'LICENSE')
    manifests = {name: read_safe(ROOT, name) for name in MANIFESTS}
    for data in manifests.values():
        if json.loads(data)['name'] != 'optimax':
            raise ValueError('invalid manifest name')
    output.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.optimax-release-', dir=output))
    retain_recovery = False
    try:
        for archive, entries in (
            ('optimax-skill.zip', {'optimax/LICENSE': license_data, **{'optimax/' + name: data for name, data in runtime.items()}}),
            ('optimax-plugin.zip', {'LICENSE': license_data, **manifests, **review_ladder, **{'skills/optimax/' + name: data for name, data in runtime.items()}}),
        ):
            with zipfile.ZipFile(staging / archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
                for name, data in sorted(entries.items()):
                    info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                    info.create_system = 3
                    info.external_attr = 0o100644 << 16
                    info.compress_type = zipfile.ZIP_DEFLATED
                    z.writestr(info, data, compresslevel=9)
        backups = {}
        for destination in destinations:
            if destination.exists():
                backup = staging / (destination.name + '.previous')
                shutil.copy2(destination, backup)
                backups[destination] = backup
        def identity(path):
            try:
                metadata = path.lstat()
            except FileNotFoundError:
                return None
            return metadata.st_dev, metadata.st_ino

        originals = {destination: identity(destination) for destination in destinations}
        attempts = []
        # Keep recovery files even if rollback itself is interrupted.
        retain_recovery = True
        try:
            for destination in destinations:
                staged = staging / destination.name
                attempts.append((destination, identity(staged)))
                os.replace(staged, destination)
        except BaseException as promotion_error:
            # Individual renames are atomic; the pair is not crash-atomic.
            rollback_errors = []
            for destination, staged_identity in reversed(attempts):
                try:
                    current = identity(destination)
                    if current == originals[destination]:
                        continue
                    if current != staged_identity:
                        raise OSError(f'unexpected replacement at {destination}')
                    if destination in backups:
                        os.replace(backups[destination], destination)
                    else:
                        destination.unlink()
                except BaseException as error:
                    rollback_errors.append(error)
            if rollback_errors:
                details = '; '.join(str(error) or type(error).__name__ for error in rollback_errors)
                raise OSError(f'release rollback failed ({details}); recovery files retained at {staging}') from promotion_error
            retain_recovery = False
            raise
        retain_recovery = False
    finally:
        if not retain_recovery:
            shutil.rmtree(staging)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    args = parser.parse_args()
    build(args.output)


if __name__ == '__main__':
    main()
