"""Build-only validation for allowlisted plugin release payloads."""
from pathlib import PurePosixPath
import re

MAX_MEMBER_BYTES = 1024 * 1024
MAX_TOTAL_BYTES = 8 * 1024 * 1024
READ_CHUNK_BYTES = 64 * 1024

# Reject common YAML implicit non-string scalars in the supported plain subset.
# YAML 1.2 octals use unsigned lowercase 0o and digits only; keep that branch case-sensitive.
NONSTRING_SCALAR = re.compile(
    r'''(?:[+-]?(?:[0-9][0-9_]*(?::[0-9_]+)*(?:\.[0-9_]*)?(?:[eE][+-]?[0-9]+)?
        |\.[0-9_]+(?:[eE][+-]?[0-9]+)?|0[xX][0-9a-fA-F_]+|0[bB][01_]+|\.inf)
        |(?-i:0o[0-7]+)|\.nan|[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}(?:[Tt \t].*)?)''',
    re.IGNORECASE | re.VERBOSE,
)


# This is the builder's supported single-line plain scalar subset, not a YAML parser.
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


def validate_entries(entries):
    total = 0
    for name, data in entries.items():
        parts = name.split('/')
        if (not name or '\\' in name or PurePosixPath(name).is_absolute()
                or any(part in ('', '.', '..') for part in parts)):
            raise ValueError(f'unsafe archive entry: {name}')
        total += len(data)
        if len(data) > MAX_MEMBER_BYTES or total > MAX_TOTAL_BYTES:
            raise ValueError('archive byte limit exceeded')
