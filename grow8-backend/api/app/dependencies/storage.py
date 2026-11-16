from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.core.config import get_api_settings
from app.storage import FileStorage, LocalFileStorage


@lru_cache
def get_file_storage() -> FileStorage:
    return LocalFileStorage(get_api_settings().file_storage_dir)


Storage = Annotated[FileStorage, Depends(get_file_storage)]
