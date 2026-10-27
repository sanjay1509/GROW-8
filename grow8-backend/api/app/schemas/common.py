from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel

from app.core.time import as_utc

# DB datetimes are naive UTC; this makes responses carry an explicit +00:00 offset.
UtcDateTime = Annotated[datetime, AfterValidator(as_utc)]


class Page[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int
