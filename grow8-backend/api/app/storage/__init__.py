"""Where uploaded files live (ADR 0007). Code depends on the FileStorage interface;
LocalFileStorage keeps files in a directory (the file_storage Docker volume)."""

from app.storage.base import FileStorage, StoredFileMissing, new_key
from app.storage.local import LocalFileStorage

__all__ = ["FileStorage", "LocalFileStorage", "StoredFileMissing", "new_key"]
