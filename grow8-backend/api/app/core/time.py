from datetime import UTC, datetime


def utcnow() -> datetime:
    """Current time as a naive UTC datetime, the form stored in MySQL DATETIME columns."""
    return datetime.now(UTC).replace(tzinfo=None)


def to_db_datetime(value: datetime) -> datetime:
    """Convert an aware datetime to naive UTC for storage."""
    return value.astimezone(UTC).replace(tzinfo=None)


def as_utc(value: datetime) -> datetime:
    """Mark a naive UTC datetime read from MySQL as UTC (aware)."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
