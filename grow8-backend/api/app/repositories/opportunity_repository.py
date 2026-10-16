from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from grow8_common.models import (
    CompensationType,
    CreatorOrganization,
    Opportunity,
    OpportunityCategory,
    OpportunityStatus,
    Skill,
    WorkMode,
)
from sqlalchemy import ColumnElement, Select, func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload


@dataclass(frozen=True)
class OpportunityQuery:
    """Filters for a listing. Which statuses/deadlines are visible is decided by the
    service layer; this module only turns the filters into SQL."""

    statuses: Sequence[OpportunityStatus] = ()
    organization_id: int | None = None
    deadline_after: datetime | None = None
    deadline_before: datetime | None = None
    text: str | None = None
    category_code: str | None = None
    skill_codes: Sequence[str] = field(default_factory=tuple)
    work_mode: WorkMode | None = None
    compensation_type: CompensationType | None = None
    min_hours: Decimal | None = None
    max_hours: Decimal | None = None


_O = Opportunity
_SORTS: dict[str, tuple[ColumnElement, ...]] = {
    "deadline": (_O.application_deadline.asc(),),
    "-deadline": (_O.application_deadline.desc(),),
    "newest": (func.coalesce(_O.published_at, _O.created_at).desc(),),
    "oldest": (func.coalesce(_O.published_at, _O.created_at).asc(),),
    "hours": (_O.expected_hours.asc(),),
    "-hours": (_O.expected_hours.desc(),),
    # unpaid opportunities have no amount; treat them as 0
    "compensation": (func.coalesce(_O.compensation_amount, 0).asc(),),
    "-compensation": (func.coalesce(_O.compensation_amount, 0).desc(),),
    "title": (_O.title.asc(),),
}

_EAGER = (
    joinedload(Opportunity.category),
    joinedload(Opportunity.organization),
    selectinload(Opportunity.skills),
)


def _conditions(query: OpportunityQuery) -> list[ColumnElement[bool]]:
    conds: list[ColumnElement[bool]] = []
    if query.statuses:
        conds.append(Opportunity.status.in_(query.statuses))
    if query.organization_id is not None:
        conds.append(Opportunity.organization_id == query.organization_id)
    if query.deadline_after is not None:
        conds.append(Opportunity.application_deadline > query.deadline_after)
    if query.deadline_before is not None:
        conds.append(Opportunity.application_deadline < query.deadline_before)
    if query.text:
        # case-insensitive via the utf8mb4_0900_ai_ci collation; % and _ are escaped
        conds.append(
            or_(
                Opportunity.title.contains(query.text, autoescape=True),
                Opportunity.description.contains(query.text, autoescape=True),
                Opportunity.organization.has(
                    CreatorOrganization.name.contains(query.text, autoescape=True)
                ),
            )
        )
    if query.category_code:
        conds.append(Opportunity.category.has(OpportunityCategory.code == query.category_code))
    if query.skill_codes:
        conds.append(Opportunity.skills.any(Skill.code.in_(query.skill_codes)))
    if query.work_mode is not None:
        conds.append(Opportunity.work_mode == query.work_mode)
    if query.compensation_type is not None:
        conds.append(Opportunity.compensation_type == query.compensation_type)
    if query.min_hours is not None:
        conds.append(Opportunity.expected_hours >= query.min_hours)
    if query.max_hours is not None:
        conds.append(Opportunity.expected_hours <= query.max_hours)
    return conds


def search(
    session: Session, query: OpportunityQuery, sort: str, limit: int, offset: int
) -> tuple[Sequence[Opportunity], int]:
    """Return one page of matches plus the total number of matches."""
    conds = _conditions(query)
    total = session.scalar(select(func.count(Opportunity.opportunity_id)).where(*conds)) or 0
    stmt = (
        select(Opportunity)
        .options(*_EAGER)
        .where(*conds)
        .order_by(*_SORTS[sort], Opportunity.opportunity_id.asc())
        .limit(limit)
        .offset(offset)
    )
    return session.scalars(stmt).unique().all(), total


def _by_id(opportunity_id: int) -> Select[tuple[Opportunity]]:
    return select(Opportunity).options(*_EAGER).where(Opportunity.opportunity_id == opportunity_id)


def get(session: Session, opportunity_id: int) -> Opportunity | None:
    return session.scalars(_by_id(opportunity_id)).unique().first()


def get_for_update(session: Session, opportunity_id: int) -> Opportunity | None:
    """Load and row-lock the opportunity until the transaction ends."""
    stmt = _by_id(opportunity_id).with_for_update(of=Opportunity)
    return session.scalars(stmt).unique().first()


def add(session: Session, opportunity: Opportunity) -> Opportunity:
    session.add(opportunity)
    session.flush()
    return opportunity
