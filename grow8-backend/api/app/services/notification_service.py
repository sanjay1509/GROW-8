"""A user's own notifications. The consumer services write them (ADR 0003); the API
only reads them and marks them read."""

from grow8_common.models import Notification, UserAccount
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.time import utcnow
from app.repositories import notification_repository
from app.schemas.common import Page
from app.schemas.notification import MarkAllReadResult, NotificationListParams, NotificationRead


def list_mine(
    session: Session, user: UserAccount, params: NotificationListParams
) -> Page[NotificationRead]:
    items, total = notification_repository.list_for_user(
        session, user.user_id, params.unread_only, params.limit, params.offset
    )
    return Page[NotificationRead](
        items=[NotificationRead.model_validate(n) for n in items],
        total=total,
        limit=params.limit,
        offset=params.offset,
    )


def unread_count(session: Session, user: UserAccount) -> int:
    return notification_repository.count_unread(session, user.user_id)


def mark_read(session: Session, user: UserAccount, notification_id: int) -> Notification:
    """Mark one of the caller's notifications read. Someone else's notification is
    reported as not found, so ids can't be probed. Marking it again keeps the
    original read_at."""
    notification = notification_repository.get_for_user(session, notification_id, user.user_id)
    if notification is None:
        raise NotFoundError("Notification not found", code="NOTIFICATION_NOT_FOUND")
    if notification.read_at is None:
        notification.read_at = utcnow()
        session.commit()
        session.refresh(notification)
    return notification


def mark_all_read(session: Session, user: UserAccount) -> MarkAllReadResult:
    marked = notification_repository.mark_all_read(session, user.user_id, utcnow())
    session.commit()
    return MarkAllReadResult(marked_read=marked)
