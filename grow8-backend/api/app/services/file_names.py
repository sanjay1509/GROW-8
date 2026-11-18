"""Display names for uploaded files (resumes, submission attachments).

A display name is only ever shown or sent back in Content-Disposition. It is never
used as a path: files are stored under server-generated keys (ADR 0007).
"""

import re
import unicodedata

MAX_LENGTH = 255  # the file_name columns are VARCHAR(255)


def clean_display_name(name: str | None, default: str, extensions: tuple[str, ...]) -> str:
    """The last path segment of `name`, without control characters, with whitespace
    collapsed, at most 255 characters, and ending in one of `extensions` (compared
    case-insensitively; `extensions[0]` is appended otherwise). `default` when
    nothing usable is left."""
    name = (name or "").replace("\\", "/").rsplit("/", 1)[-1]
    name = "".join(
        c for c in unicodedata.normalize("NFC", name) if unicodedata.category(c)[0] != "C"
    )
    name = re.sub(r"\s+", " ", name).strip(" .")
    if not name:
        return default
    if not name.lower().endswith(extensions):
        name = f"{name}{extensions[0]}"
    if len(name) <= MAX_LENGTH:
        return name
    return name[: MAX_LENGTH - len(extensions[0])] + extensions[0]
