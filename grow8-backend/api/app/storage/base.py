import re
from collections.abc import Iterable
from typing import BinaryIO, Protocol
from uuid import uuid4

# <purpose>/<uuid4 hex>, e.g. "resumes/3f2c9b0e5d6a4f1e8b7c6d5e4f3a2b1c". Keys are always
# made by new_key(), never from a file name, so they can't name a path outside the store.
KEY_PATTERN = re.compile(r"^[a-z]+/[0-9a-f]{32}$")


class StoredFileMissing(Exception):
    """The key is valid but no file is stored under it."""


def new_key(purpose: str) -> str:
    """A fresh, unguessable storage key for a file of the given purpose."""
    key = f"{purpose}/{uuid4().hex}"
    if not KEY_PATTERN.fullmatch(key):
        raise ValueError(f"invalid purpose {purpose!r}")
    return key


def check_key(key: str) -> str:
    if not KEY_PATTERN.fullmatch(key):
        raise ValueError(f"invalid storage key {key!r}")
    return key


class FileStorage(Protocol):
    def save(self, key: str, chunks: Iterable[bytes]) -> None:
        """Store the bytes under `key` atomically: readers see the whole file or none.
        If `chunks` raises, nothing is left behind and the error propagates."""
        ...

    def open(self, key: str) -> BinaryIO:
        """Open the stored file for reading. Raises StoredFileMissing."""
        ...

    def delete(self, key: str) -> None:
        """Remove the file. Deleting a missing key is not an error."""
        ...
