from collections.abc import Sequence
from datetime import datetime

from grow8_common.models import Notification
from sqlalchemy import ColumnElement, func, select, update
from sqlalchemy.orm import Session


def _of_user(user_id: int, unread_only: bool = False) -> list[ColumnElement[bool]]:
    conds = [Notification.user_id == user_id]
    if unread_only:
        conds.append(Notification.read_at.is_(None))
    return conds


def list_for_user(
    session: Session, user_id: int, unread_only: bool, limit: int, offset: int
) -> tuple[Sequence[Notification], int]:
    """One page of the user's notifications, newest first, plus the total."""
    conds = _of_user(user_id, unread_only)
    total = session.scalar(select(func.count(Notification.notification_id)).where(*conds)) or 0
    stmt = (
        select(Notification)
        .where(*conds)
        .order_by(Notification.created_at.desc(), Notification.notification_id.desc())
        .limit(limit)
        .offset(offset)
    )
    return session.scalars(stmt).all(), total


def count_unread(session: Session, user_id: int) -> int:
    stmt = select(func.count(Notification.notification_id)).where(*_of_user(user_id, True))
    return session.scalar(stmt) or 0


def get_for_user(session: Session, notification_id: int, user_id: int) -> Notification | None:
    stmt = select(Notification).where(
        Notification.notification_id == notification_id, Notification.user_id == user_id
    )
    return session.scalars(stmt).first()


def mark_all_read(session: Session, user_id: int, read_at: datetime) -> int:
    """Set read_at on every unread notification of the user; returns how many changed."""
    result = session.execute(
        update(Notification).where(*_of_user(user_id, True)).values(read_at=read_at)
    )
    return result.rowcount
