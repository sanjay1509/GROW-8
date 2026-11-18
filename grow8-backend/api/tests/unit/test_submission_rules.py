"""Work submission rules that need no database (ADR 0012)."""

import io
import zipfile

import pytest

from app.services.submission_rules import (
    CSV,
    DOCX,
    JPEG,
    MAX_FILE_BYTES,
    MAX_FILES,
    MAX_REQUEST_BYTES,
    PDF,
    PNG,
    SNIFF_BYTES,
    TXT,
    XLSX,
    clean_file_name,
    detect_type,
    is_zip,
)


def _zip(*entries: str) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for entry in entries:
            archive.writestr(entry, "<xml/>")
    return buffer.getvalue()


def _entries(data: bytes) -> list[str]:
    return zipfile.ZipFile(io.BytesIO(data)).namelist()


# ---------------------------------------------------------------------------
# Limits
# ---------------------------------------------------------------------------


def test_limits_match_adr_0012() -> None:
    assert MAX_FILES == 5
    assert MAX_FILE_BYTES == 5 * 1024 * 1024
    assert MAX_REQUEST_BYTES > MAX_FILES * MAX_FILE_BYTES


# ---------------------------------------------------------------------------
# Detecting the type from the content
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("head", "expected"),
    [
        (b"%PDF-1.7\n...", PDF),
        (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR", PNG),
        (b"\xff\xd8\xff\xe0\x00\x10JFIF", JPEG),
    ],
)
def test_signatures_are_recognised(head: bytes, expected: object) -> None:
    assert detect_type(head, "whatever.bin") is expected


def test_the_name_does_not_decide_the_type() -> None:
    assert detect_type(b"%PDF-1.4", "photo.png") is PDF
    assert detect_type(b"MZ\x90\x00\x03\x00\x00\x00", "report.pdf") is None  # a Windows .exe


def test_docx_and_xlsx_are_recognised_from_their_entries() -> None:
    docx = _zip("[Content_Types].xml", "_rels/.rels", "word/document.xml")
    xlsx = _zip("[Content_Types].xml", "_rels/.rels", "xl/workbook.xml")

    assert is_zip(docx[:SNIFF_BYTES])
    assert detect_type(docx[:SNIFF_BYTES], "a.docx", _entries(docx)) is DOCX
    assert detect_type(xlsx[:SNIFF_BYTES], "a.xlsx", _entries(xlsx)) is XLSX


@pytest.mark.parametrize(
    "entries",
    [
        ("notes.txt", "photo.jpg"),  # an ordinary zip
        ("word/document.xml",),  # no [Content_Types].xml
        ("[Content_Types].xml", "ppt/presentation.xml"),  # PowerPoint isn't allowed
    ],
)
def test_other_zip_archives_are_refused(entries: tuple[str, ...]) -> None:
    data = _zip(*entries)
    assert detect_type(data[:SNIFF_BYTES], "a.docx", _entries(data)) is None


def test_a_zip_whose_entries_could_not_be_read_is_refused() -> None:
    assert detect_type(b"PK\x03\x04broken", "a.docx", ()) is None


@pytest.mark.parametrize(
    ("name", "expected"),
    [("hours.csv", CSV), ("HOURS.CSV", CSV), ("notes.txt", TXT), ("notes", TXT), (None, TXT)],
)
def test_text_is_csv_or_plain_text_by_name(name: str | None, expected: object) -> None:
    assert detect_type(b"date,hours\n2026-11-01,3.5\r\n", name) is expected


def test_a_character_cut_off_by_the_sniff_window_is_still_text() -> None:
    text = b"a" * (SNIFF_BYTES - 1) + "é and more".encode()
    head = text[:SNIFF_BYTES]  # ends with the first of the two bytes of "é"
    assert head.endswith(b"\xc3")
    assert detect_type(head, "rota.txt") is TXT


def test_a_whole_file_ending_in_half_a_character_is_not_text() -> None:
    assert detect_type("Café".encode()[:-1], "rota.txt") is None


@pytest.mark.parametrize(
    "head",
    [
        b"",  # empty
        b"name\x00\x00\x00",  # NUL bytes
        b"\x1b[31mred",  # other control characters
        b"caf\xe9",  # Latin-1, not UTF-8
    ],
)
def test_binary_or_non_utf8_data_is_not_text(head: bytes) -> None:
    assert detect_type(head, "data.csv") is None


# ---------------------------------------------------------------------------
# Display names
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("given", "file_type", "stored"),
    [
        ("count-sheets.pdf", PDF, "count-sheets.pdf"),
        ("Photo.JPEG", JPEG, "Photo.JPEG"),
        ("photo.jpg", JPEG, "photo.jpg"),
        ("photo", JPEG, "photo.jpg"),
        ("notes.exe", TXT, "notes.exe.txt"),
        ("../../etc/passwd", TXT, "passwd.txt"),
        (r"C:\Users\alex\Hours 2026.xlsx", XLSX, "Hours 2026.xlsx"),
        ("bad\x00name\n.docx", DOCX, "badname.docx"),
        (None, CSV, "attachment.csv"),
        ("  ...  ", PNG, "attachment.png"),
    ],
)
def test_file_names_are_display_only_and_match_the_type(
    given: str | None, file_type: object, stored: str
) -> None:
    assert clean_file_name(given, file_type) == stored


def test_long_file_names_are_cut_but_keep_a_matching_extension() -> None:
    name = clean_file_name("x" * 400 + ".xlsx", XLSX)
    assert len(name) == 255
    assert name.endswith(".xlsx")
