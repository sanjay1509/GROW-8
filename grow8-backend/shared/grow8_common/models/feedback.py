from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from grow8_common.models.base import Base, UnsignedInt, created_at_column, enum_column
from grow8_common.models.enums import ReviewDecision


class Feedback(Base):
    """Feedback with no AdminReview row is pending."""

    __tablename__ = "feedback"
    __table_args__ = (
        UniqueConstraint("application_id", "author_user_id", name="uq_feedback_application_author"),
        Index("ix_feedback_author", "author_user_id"),
        Index("ix_feedback_subject", "subject_user_id"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="chk_feedback_rating"),
        CheckConstraint("author_user_id <> subject_user_id", name="chk_feedback_not_self"),
    )

    feedback_id: Mapped[int] = mapped_column(UnsignedInt, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(
        UnsignedInt,
        ForeignKey("application.application_id", name="fk_feedback_application"),
    )
    author_user_id: Mapped[int] = mapped_column(
        UnsignedInt, ForeignKey("user_account.user_id", name="fk_feedback_author")
    )
    subject_user_id: Mapped[int] = mapped_column(
        UnsignedInt, ForeignKey("user_account.user_id", name="fk_feedback_subject")
    )
    rating: Mapped[int] = mapped_column(TINYINT(unsigned=True))
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()


class AdminReview(Base):
    __tablename__ = "admin_review"
    __table_args__ = (
        UniqueConstraint("feedback_id", name="uq_admin_review_feedback"),
        Index("ix_admin_review_admin", "admin_user_id"),
    )

    review_id: Mapped[int] = mapped_column(UnsignedInt, primary_key=True, autoincrement=True)
    feedback_id: Mapped[int] = mapped_column(
        UnsignedInt, ForeignKey("feedback.feedback_id", name="fk_admin_review_feedback")
    )
    admin_user_id: Mapped[int] = mapped_column(
        UnsignedInt, ForeignKey("user_account.user_id", name="fk_admin_review_admin")
    )
    decision: Mapped[ReviewDecision] = mapped_column(enum_column(ReviewDecision))
    reason: Mapped[str | None] = mapped_column(String(500))
    reviewed_at: Mapped[datetime] = created_at_column()
