import re

from unidecode import unidecode

default_char_replacements = (
    (re.compile('[\s:;/]+'), '_'),
    (re.compile('[^a-z0-9-._]'), ''),
    (re.compile('[-._]+$'), ''),
)


def default_sanitize_path(folder_or_file_name: str) -> str:
    sanitized = unidecode(folder_or_file_name)
    sanitized = sanitized.lower()
    for regex, replacement in default_char_replacements:
        sanitized = regex.sub(replacement, sanitized)
    return sanitized
