from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import Mapped, mapped_column

from grow8_common.models.base import Base, UnsignedInt, created_at_column, enum_column
from grow8_common.models.enums import ApplicationStatus, ReviewDecision


class Application(Base):
    __tablename__ = "application"
    __table_args__ = (
        UniqueConstraint(
            "contributor_id", "opportunity_id", name="uq_application_contributor_opportunity"
        ),
        Index("ix_application_opportunity_status", "opportunity_id", "status"),
        CheckConstraint(
            "status IN ('pending', 'withdrawn') OR decided_at IS NOT NULL",
            name="chk_application_decided",
        ),
    )

    application_id: Mapped[int] = mapped_column(UnsignedInt, primary_key=True, autoincrement=True)
    opportunity_id: Mapped[int] = mapped_column(
        UnsignedInt,
        ForeignKey("opportunity.opportunity_id", name="fk_application_opportunity"),
    )
    contributor_id: Mapped[int] = mapped_column(
        UnsignedInt,
        ForeignKey("contributor_profile.user_id", name="fk_application_contributor"),
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        enum_column(ApplicationStatus), server_default=ApplicationStatus.PENDING.value
    )
    motivation: Mapped[str | None] = mapped_column(Text)
    submitted_at: Mapped[datetime] = created_at_column()
    decided_at: Mapped[datetime | None] = mapped_column(DateTime)


class WorkSubmission(Base):
    __tablename__ = "work_submission"
    __table_args__ = (
        UniqueConstraint("application_id", name="uq_work_submission_application"),
        CheckConstraint("hours_claimed > 0", name="chk_work_submission_hours"),
    )

    submission_id: Mapped[int] = mapped_column(UnsignedInt, primary_key=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(
        UnsignedInt,
        ForeignKey("application.application_id", name="fk_work_submission_application"),
    )
    description: Mapped[str] = mapped_column(Text)
    hours_claimed: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    submitted_at: Mapped[datetime] = created_at_column()


class SubmissionAttachment(Base):
    __tablename__ = "submission_attachment"
    __table_args__ = (
        UniqueConstraint("storage_key", name="uq_submission_attachment_storage_key"),
        Index("ix_submission_attachment_submission", "submission_id"),
    )

    attachment_id: Mapped[int] = mapped_column(UnsignedInt, primary_key=True, autoincrement=True)
    submission_id: Mapped[int] = mapped_column(
        UnsignedInt,
        ForeignKey(
            "work_submission.submission_id",
            name="fk_submission_attachment_submission",
            ondelete="CASCADE",
        ),
    )
    file_name: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(BIGINT(unsigned=True))
    storage_key: Mapped[str] = mapped_column(String(512))
    uploaded_at: Mapped[datetime] = created_at_column()


class WorkVerification(Base):
    __tablename__ = "work_verification"
    __table_args__ = (
        UniqueConstraint("submission_id", name="uq_work_verification_submission"),
        Index("ix_work_verification_verified_by", "verified_by_user_id"),
        CheckConstraint(
            "(decision = 'approved' AND verified_hours IS NOT NULL AND verified_hours > 0) "
            "OR (decision = 'rejected' AND verified_hours IS NULL)",
            name="chk_work_verification_hours",
        ),
    )

    verification_id: Mapped[int] = mapped_column(
        UnsignedInt, primary_key=True, autoincrement=True
    )
    submission_id: Mapped[int] = mapped_column(
        UnsignedInt,
        ForeignKey("work_submission.submission_id", name="fk_work_verification_submission"),
    )
    verified_by_user_id: Mapped[int] = mapped_column(
        UnsignedInt,
        ForeignKey("user_account.user_id", name="fk_work_verification_verified_by"),
    )
    decision: Mapped[ReviewDecision] = mapped_column(enum_column(ReviewDecision))
    verified_hours: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    comment: Mapped[str | None] = mapped_column(Text)
    verified_at: Mapped[datetime] = created_at_column()
