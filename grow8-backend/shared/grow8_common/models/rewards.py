from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from grow8_common.models.base import Base, UnsignedInt, created_at_column, enum_column
from grow8_common.models.enums import PointSource


class Badge(Base):
    __tablename__ = "badge"
    __table_args__ = (
        UniqueConstraint("code", name="uq_badge_code"),
        UniqueConstraint("name", name="uq_badge_name"),
    )

    badge_id: Mapped[int] = mapped_column(UnsignedInt, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String(255))
    points: Mapped[int] = mapped_column(UnsignedInt, server_default="0")
    required_verified_hours: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))


class ContributorBadge(Base):
    __tablename__ = "contributor_badge"
    __table_args__ = (Index("ix_contributor_badge_badge", "badge_id"),)

    contributor_id: Mapped[int] = mapped_column(
        UnsignedInt,
        ForeignKey(
            "contributor_profile.user_id",
            name="fk_contributor_badge_contributor",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )
    badge_id: Mapped[int] = mapped_column(
        UnsignedInt,
        ForeignKey("badge.badge_id", name="fk_contributor_badge_badge"),
        primary_key=True,
    )
    awarded_at: Mapped[datetime] = created_at_column()


class PointTransaction(Base):
    """Leaderboard totals are SUM(points) over this table, never stored."""

    __tablename__ = "point_transaction"
    __table_args__ = (
        UniqueConstraint("verification_id", name="uq_point_transaction_verification"),
        UniqueConstraint(
            "contributor_id", "badge_id", name="uq_point_transaction_contributor_badge"
        ),
        Index("ix_point_transaction_badge", "badge_id"),
        # Badge points only for a badge this contributor earned (NULL badge_id: not checked).
        ForeignKeyConstraint(
            ["contributor_id", "badge_id"],
            ["contributor_badge.contributor_id", "contributor_badge.badge_id"],
            name="fk_point_transaction_contributor_badge",
        ),
        CheckConstraint(
            "(source = 'work_verified' AND verification_id IS NOT NULL AND badge_id IS NULL) "
            "OR (source = 'badge_awarded' AND badge_id IS NOT NULL AND verification_id IS NULL)",
            name="chk_point_transaction_source",
        ),
    )

    transaction_id: Mapped[int] = mapped_column(UnsignedInt, primary_key=True, autoincrement=True)
    contributor_id: Mapped[int] = mapped_column(
        UnsignedInt,
        ForeignKey("contributor_profile.user_id", name="fk_point_transaction_contributor"),
    )
    points: Mapped[int] = mapped_column(Integer)
    source: Mapped[PointSource] = mapped_column(enum_column(PointSource))
    verification_id: Mapped[int | None] = mapped_column(
        UnsignedInt,
        ForeignKey(
            "work_verification.verification_id", name="fk_point_transaction_verification"
        ),
    )
    badge_id: Mapped[int | None] = mapped_column(UnsignedInt)
    created_at: Mapped[datetime] = created_at_column()
