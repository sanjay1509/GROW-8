"""How the consumer services tell users about things: one `notification` row per user
per event, which the API serves to the frontend (ADR 0003)."""

from typing import Protocol
from uuid import UUID

from sqlalchemy import insert
from sqlalchemy.orm import Session

from grow8_common.models import Notification, NotificationType

TITLE_MAX = 200
MESSAGE_MAX = 500


class Notifier(Protocol):
    def notify(
        self, user_id: int, title: str, message: str, *, opportunity_id: int | None = None
    ) -> None: ...


def _fit(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


class DbNotifier:
    """Adds notification rows to `session` for one event. It does not commit: the
    caller commits once the whole event is handled, before the message is acked.

    UNIQUE (event_id, user_id) + INSERT IGNORE makes a redelivered event a no-op.
    """

    def __init__(
        self, session: Session, event_id: UUID, notification_type: NotificationType
    ) -> None:
        self._session = session
        self._event_id = str(event_id)
        self._type = notification_type

    def notify(
        self, user_id: int, title: str, message: str, *, opportunity_id: int | None = None
    ) -> None:
        self._session.execute(
            insert(Notification)
            .prefix_with("IGNORE")
            .values(
                user_id=user_id,
                event_id=self._event_id,
                notification_type=self._type,
                title=_fit(title, TITLE_MAX),
                message=_fit(message, MESSAGE_MAX),
                opportunity_id=opportunity_id,
            )
        )
