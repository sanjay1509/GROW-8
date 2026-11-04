from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import SMALLINT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from grow8_common.models.base import (
    Base,
    UnsignedInt,
    created_at_column,
    enum_column,
    updated_at_column,
)
from grow8_common.models.enums import CompensationType, OpportunityStatus, SkillSource, WorkMode
from grow8_common.models.users import CreatorOrganization


class OpportunityCategory(Base):
    __tablename__ = "opportunity_category"
    __table_args__ = (
        UniqueConstraint("code", name="uq_opportunity_category_code"),
        UniqueConstraint("name", name="uq_opportunity_category_name"),
    )

    category_id: Mapped[int] = mapped_column(UnsignedInt, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String(255))


class Skill(Base):
    __tablename__ = "skill"
    __table_args__ = (
        UniqueConstraint("code", name="uq_skill_code"),
        UniqueConstraint("name", name="uq_skill_name"),
    )

    skill_id: Mapped[int] = mapped_column(UnsignedInt, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(100))


# Pure association table (no extra columns), so it is mapped as a Table.
opportunity_skill = Table(
    "opportunity_skill",
    Base.metadata,
    Column(
        "opportunity_id",
        UnsignedInt,
        ForeignKey(
            "opportunity.opportunity_id",
            name="fk_opportunity_skill_opportunity",
            ondelete="CASCADE",
        ),
        primary_key=True,
    ),
    Column(
        "skill_id",
        UnsignedInt,
        ForeignKey("skill.skill_id", name="fk_opportunity_skill_skill"),
        primary_key=True,
    ),
    Index("ix_opportunity_skill_skill", "skill_id"),
)


class Opportunity(Base):
    __tablename__ = "opportunity"
    __table_args__ = (
        Index("ix_opportunity_status_deadline", "status", "application_deadline"),
        Index("ix_opportunity_category_status", "category_id", "status"),
        Index("ix_opportunity_organization_status", "organization_id", "status"),
        Index("ix_opportunity_published_at", "published_at"),
        CheckConstraint("expected_hours > 0", name="chk_opportunity_expected_hours"),
        CheckConstraint("compensation_amount >= 0", name="chk_opportunity_compensation_amount"),
        CheckConstraint("applicant_limit > 0", name="chk_opportunity_applicant_limit"),
        CheckConstraint("end_date >= start_date", name="chk_opportunity_dates"),
        CheckConstraint(
            "status = 'draft' OR ("
            "requirements IS NOT NULL AND start_date IS NOT NULL AND end_date IS NOT NULL "
            "AND expected_hours IS NOT NULL AND compensation_type IS NOT NULL "
            "AND (compensation_type = 'unpaid' OR compensation_amount IS NOT NULL) "
            "AND applicant_limit IS NOT NULL AND application_deadline IS NOT NULL "
            "AND working_conditions IS NOT NULL AND safety_information IS NOT NULL "
            "AND accessibility_details IS NOT NULL AND published_at IS NOT NULL)",
            name="chk_opportunity_published_complete",
        ),
    )

    opportunity_id: Mapped[int] = mapped_column(UnsignedInt, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        UnsignedInt,
        ForeignKey("creator_organization.organization_id", name="fk_opportunity_organization"),
    )
    category_id: Mapped[int] = mapped_column(
        UnsignedInt,
        ForeignKey("opportunity_category.category_id", name="fk_opportunity_category"),
    )
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    requirements: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(255))
    work_mode: Mapped[WorkMode | None] = mapped_column(enum_column(WorkMode))
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    expected_hours: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    compensation_type: Mapped[CompensationType | None] = mapped_column(
        enum_column(CompensationType)
    )
    compensation_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    compensation_details: Mapped[str | None] = mapped_column(String(500))
    applicant_limit: Mapped[int | None] = mapped_column(SMALLINT(unsigned=True))
    application_deadline: Mapped[datetime | None] = mapped_column(DateTime)
    working_conditions: Mapped[str | None] = mapped_column(Text)
    safety_information: Mapped[str | None] = mapped_column(Text)
    accessibility_details: Mapped[str | None] = mapped_column(Text)
    status: Mapped[OpportunityStatus] = mapped_column(
        enum_column(OpportunityStatus), server_default=OpportunityStatus.DRAFT.value
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    organization: Mapped[CreatorOrganization] = relationship()
    category: Mapped[OpportunityCategory] = relationship()
    skills: Mapped[list[Skill]] = relationship(secondary=opportunity_skill, order_by=Skill.code)


class ContributorSkill(Base):
    __tablename__ = "contributor_skill"
    __table_args__ = (Index("ix_contributor_skill_skill", "skill_id"),)

    contributor_id: Mapped[int] = mapped_column(
        UnsignedInt,
        ForeignKey(
            "contributor_profile.user_id",
            name="fk_contributor_skill_contributor",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )
    skill_id: Mapped[int] = mapped_column(
        UnsignedInt,
        ForeignKey("skill.skill_id", name="fk_contributor_skill_skill"),
        primary_key=True,
    )
    source: Mapped[SkillSource] = mapped_column(
        enum_column(SkillSource), server_default=SkillSource.SELF_REPORTED.value
    )
    created_at: Mapped[datetime] = created_at_column()
