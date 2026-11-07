"""Collect textual license notices without bundling similarly named test binaries."""
from pathlib import Path
import re


def notice_candidate(path):
    path=Path(path)
    named=bool(re.match(r'^(licen[cs]e|copying|notice)(?:$|[._-])',path.name,re.I))
    directory=any(part.lower() in ('licenses','licences') for part in path.parts[:-1])
    return (named or directory) and not path.is_absolute() and '..' not in path.parts


def is_notice(path, content):
    if not notice_candidate(path) or b'\x00' in content:return False
    try:content.decode('utf-8-sig')
    except UnicodeDecodeError:return False
    return True
