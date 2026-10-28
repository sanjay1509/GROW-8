from datetime import datetime

from sqlalchemy import CHAR, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from grow8_common.models.base import Base, UnsignedInt, created_at_column, enum_column
from grow8_common.models.enums import NotificationType


class Notification(Base):
    """What a user was told, kept as written. One row per user per event (the
    idempotency key for redelivered events); read_at NULL means unread."""

    __tablename__ = "notification"
    __table_args__ = (
        UniqueConstraint("event_id", "user_id", name="uq_notification_event_user"),
        Index("ix_notification_user_read_created", "user_id", "read_at", "created_at"),
    )

    notification_id: Mapped[int] = mapped_column(UnsignedInt, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        UnsignedInt,
        ForeignKey("user_account.user_id", name="fk_notification_user", ondelete="CASCADE"),
    )
    event_id: Mapped[str] = mapped_column(CHAR(36))
    notification_type: Mapped[NotificationType] = mapped_column(enum_column(NotificationType))
    title: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(String(500))
    opportunity_id: Mapped[int | None] = mapped_column(
        UnsignedInt,
        ForeignKey(
            "opportunity.opportunity_id", name="fk_notification_opportunity", ondelete="SET NULL"
        ),
    )
    read_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = created_at_column()
