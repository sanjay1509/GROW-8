from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.dependencies.auth import CurrentUser, DbSession
from app.schemas.common import Page
from app.schemas.notification import (
    MarkAllReadResult,
    NotificationListParams,
    NotificationRead,
    UnreadCount,
)
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])

NotificationId = Annotated[int, Path(ge=1)]


@router.get("", response_model=Page[NotificationRead])
def list_notifications(
    params: Annotated[NotificationListParams, Query()], session: DbSession, user: CurrentUser
) -> Page[NotificationRead]:
    """The caller's notifications, newest first. `unread_only=true` for the unread ones."""
    return notification_service.list_mine(session, user, params)


@router.get("/unread-count", response_model=UnreadCount)
def get_unread_count(session: DbSession, user: CurrentUser) -> UnreadCount:
    """Cheap enough to poll for a notification badge."""
    return UnreadCount(unread_count=notification_service.unread_count(session, user))


@router.patch("/{notification_id}/read", response_model=NotificationRead)
def mark_notification_read(
    notification_id: NotificationId, session: DbSession, user: CurrentUser
) -> NotificationRead:
    """Mark one of your notifications read. Safe to repeat."""
    notification = notification_service.mark_read(session, user, notification_id)
    return NotificationRead.model_validate(notification)


@router.post("/read-all", response_model=MarkAllReadResult)
def mark_all_notifications_read(session: DbSession, user: CurrentUser) -> MarkAllReadResult:
    """Mark all of your unread notifications read."""
    return notification_service.mark_all_read(session, user)
