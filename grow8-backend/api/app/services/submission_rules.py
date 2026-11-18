"""Work submission rules that need no database (ADR 0012).

An attachment's type is decided from its content, never from its name or the
client's Content-Type, and the detected type is what gets stored and served.
"""

import codecs
from collections.abc import Collection
from dataclasses import dataclass

from app.services.file_names import clean_display_name

MAX_FILES = 5
MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MB per attachment
# Every file at its limit plus room for the form fields, boundaries and part headers.
MAX_REQUEST_BYTES = MAX_FILES * MAX_FILE_BYTES + 64 * 1024

# How much of a file the service reads up front to recognise it. Text files are
# judged on this much; downloads are always sent as attachments with nosniff.
SNIFF_BYTES = 8 * 1024

ZIP_SIGNATURE = b"PK\x03\x04"


@dataclass(frozen=True)
class FileType:
    content_type: str
    extensions: tuple[str, ...]  # the first one is appended to names that lack them all


PDF = FileType("application/pdf", (".pdf",))
PNG = FileType("image/png", (".png",))
JPEG = FileType("image/jpeg", (".jpg", ".jpeg"))
DOCX = FileType(
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document", (".docx",)
)
XLSX = FileType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", (".xlsx",))
CSV = FileType("text/csv", (".csv",))
TXT = FileType("text/plain", (".txt",))

_SIGNATURES = (
    (b"%PDF-", PDF),
    (b"\x89PNG\r\n\x1a\n", PNG),
    (b"\xff\xd8\xff", JPEG),
)
# Text may contain tab, newline, form feed and carriage return, but no other C0 control
# characters (NUL among them): those mean the file is binary.
_TEXT_CONTROLS = frozenset(chr(c) for c in range(32)) - {"\t", "\n", "\f", "\r"}


def is_zip(head: bytes) -> bool:
    """DOCX and XLSX are ZIP archives; the service lists the entries of these."""
    return head.startswith(ZIP_SIGNATURE)


def detect_type(
    head: bytes, file_name: str | None, zip_entries: Collection[str] = ()
) -> FileType | None:
    """The allowed type of a file starting with `head`, or None if it isn't one.

    `zip_entries` are the archive's entry names, needed only when `is_zip(head)`.
    A text file is CSV when its name ends in .csv and plain text otherwise.
    """
    if not head:
        return None
    for signature, file_type in _SIGNATURES:
        if head.startswith(signature):
            return file_type
    if is_zip(head):
        return _office_type(zip_entries)
    if _is_text(head):
        return CSV if (file_name or "").lower().endswith(".csv") else TXT
    return None


def _office_type(entries: Collection[str]) -> FileType | None:
    """Office Open XML files have [Content_Types].xml and a word/ or xl/ part."""
    if "[Content_Types].xml" not in entries:
        return None
    if any(e.startswith("word/") for e in entries):
        return DOCX
    if any(e.startswith("xl/") for e in entries):
        return XLSX
    return None


def _is_text(head: bytes) -> bool:
    """UTF-8 with no control characters other than whitespace. A multi-byte character
    cut off at the end is fine only when `head` is a full SNIFF_BYTES window, i.e. the
    file goes on; a shorter `head` is the whole file and must decode completely."""
    try:
        decoder = codecs.getincrementaldecoder("utf-8")()
        text = decoder.decode(head, final=len(head) < SNIFF_BYTES)
    except UnicodeDecodeError:
        return False
    return not _TEXT_CONTROLS.intersection(text)


def clean_file_name(name: str | None, file_type: FileType) -> str:
    """A display name ending in an extension that matches the detected type, so a
    text file named "notes.exe" is offered for download as "notes.exe.txt"."""
    return clean_display_name(name, f"attachment{file_type.extensions[0]}", file_type.extensions)
