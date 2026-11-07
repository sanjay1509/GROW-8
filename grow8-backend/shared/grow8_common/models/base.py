from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.mysql import INTEGER
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

UnsignedInt = INTEGER(unsigned=True)


class Base(DeclarativeBase):
    pass


def enum_column(enum_cls: type[Enum]) -> SAEnum:
    """MySQL ENUM storing the Python enum's *values* (e.g. 'on_site'), as in the DDL."""
    return SAEnum(
        enum_cls,
        values_callable=lambda members: [m.value for m in members],
        native_enum=True,
        validate_strings=True,
    )


def created_at_column() -> Mapped[datetime]:
    return mapped_column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))


def updated_at_column() -> Mapped[datetime]:
    return mapped_column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
    )
