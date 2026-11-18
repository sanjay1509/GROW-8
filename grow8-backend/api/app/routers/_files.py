"""Streaming a stored file (resume, submission attachment) back as a download."""

import unicodedata
from collections.abc import Iterator
from typing import BinaryIO, Protocol
from urllib.parse import quote

from fastapi.responses import StreamingResponse

_CHUNK = 64 * 1024


class Download(Protocol):
    stream: BinaryIO
    file_name: str
    content_type: str
    size_bytes: int


def content_disposition(file_name: str, fallback: str) -> str:
    """attachment with an ASCII fallback name plus the exact UTF-8 name (RFC 6266/5987)."""
    decomposed = unicodedata.normalize("NFKD", file_name)  # é -> e + accent, then drop the accent
    ascii_name = decomposed.encode("ascii", "ignore").decode().replace('"', "") or fallback
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(file_name)}"


def stream_download(file: Download, fallback_name: str) -> StreamingResponse:
    """Always an attachment, never rendered by the browser, never cached."""

    def chunks() -> Iterator[bytes]:
        with file.stream as stream:
            while chunk := stream.read(_CHUNK):
                yield chunk

    return StreamingResponse(
        chunks(),
        media_type=file.content_type,
        headers={
            "Content-Disposition": content_disposition(file.file_name, fallback_name),
            "Content-Length": str(file.size_bytes),
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )
