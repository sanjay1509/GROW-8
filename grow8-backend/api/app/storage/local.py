import os
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import BinaryIO

from app.storage.base import StoredFileMissing, check_key


class LocalFileStorage:
    """Files in a directory tree: `<root>/<purpose>/<uuid>`."""

    def __init__(self, root: str | Path) -> None:
        self._root = Path(root).resolve()

    def _path(self, key: str) -> Path:
        path = (self._root / check_key(key)).resolve()
        if not path.is_relative_to(self._root):  # defence in depth; check_key already
            raise ValueError(f"storage key {key!r} leaves the storage root")
        return path

    def save(self, key: str, chunks: Iterable[bytes]) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Write next to the target, then rename: os.replace is atomic on one filesystem.
        fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=".upload-")
        try:
            with os.fdopen(fd, "wb") as tmp:
                for chunk in chunks:
                    tmp.write(chunk)
                tmp.flush()
                os.fsync(tmp.fileno())
            os.replace(tmp_name, path)
        except BaseException:
            Path(tmp_name).unlink(missing_ok=True)
            raise

    def open(self, key: str) -> BinaryIO:
        try:
            return self._path(key).open("rb")
        except FileNotFoundError as exc:
            raise StoredFileMissing(key) from exc

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)
