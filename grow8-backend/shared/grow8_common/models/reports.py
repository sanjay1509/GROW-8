from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from grow8_common.models.base import Base, UnsignedInt, created_at_column, enum_column
from grow8_common.models.enums import ReportDecision, ReportReason

if TYPE_CHECKING:
    from grow8_common.models.opportunities import Opportunity
    from grow8_common.models.users import UserAccount


class OpportunityReport(Base):
    """A contributor's report about a published opportunity (ADR 0016). A report with
    no ReportReview row is pending."""

    __tablename__ = "opportunity_report"
    __table_args__ = (
        UniqueConstraint(
            "opportunity_id", "reporter_user_id", name="uq_opportunity_report_reporter"
        ),
        Index("ix_opportunity_report_reporter", "reporter_user_id"),
    )

    report_id: Mapped[int] = mapped_column(UnsignedInt, primary_key=True, autoincrement=True)
    opportunity_id: Mapped[int] = mapped_column(
        UnsignedInt,
        ForeignKey("opportunity.opportunity_id", name="fk_opportunity_report_opportunity"),
    )
    reporter_user_id: Mapped[int] = mapped_column(
        UnsignedInt, ForeignKey("user_account.user_id", name="fk_opportunity_report_reporter")
    )
    reason: Mapped[ReportReason] = mapped_column(enum_column(ReportReason))
    details: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created_at_column()

    opportunity: Mapped["Opportunity"] = relationship()
    reporter: Mapped["UserAccount"] = relationship()
    # At most one (uq_report_review_report); None while pending.
    review: Mapped["ReportReview | None"] = relationship()


class ReportReview(Base):
    __tablename__ = "report_review"
    __table_args__ = (
        UniqueConstraint("report_id", name="uq_report_review_report"),
        Index("ix_report_review_admin", "admin_user_id"),
        CheckConstraint(
            "decision = 'dismissed' OR reason IS NOT NULL", name="chk_report_review_reason"
        ),
    )

    review_id: Mapped[int] = mapped_column(UnsignedInt, primary_key=True, autoincrement=True)
    report_id: Mapped[int] = mapped_column(
        UnsignedInt, ForeignKey("opportunity_report.report_id", name="fk_report_review_report")
    )
    admin_user_id: Mapped[int] = mapped_column(
        UnsignedInt, ForeignKey("user_account.user_id", name="fk_report_review_admin")
    )
    decision: Mapped[ReportDecision] = mapped_column(enum_column(ReportDecision))
    reason: Mapped[str | None] = mapped_column(String(500))
    reviewed_at: Mapped[datetime] = created_at_column()
