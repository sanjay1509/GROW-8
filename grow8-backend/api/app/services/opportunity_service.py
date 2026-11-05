
from collections.abc import Sequence
from typing import Any

from grow8_common.events import EventType, OpportunityCreatedPayload
from grow8_common.models import (
    Opportunity,
    OpportunityCategory,
    OpportunityStatus,
    Skill,
    UserAccount,
)
from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    UnprocessableError,
)
from app.core.time import as_utc, to_db_datetime, utcnow
from app.events.publisher import EventPublisher
from app.repositories import (
    opportunity_repository,
    reference_repository,
    user_repository,
)
from app.repositories.opportunity_repository import OpportunityQuery
from app.schemas.common import Page
from app.schemas.opportunity import (
    MyOpportunitySearchParams,
    OpportunityCreate,
    OpportunityRead,
    OpportunitySearchParams,
    OpportunityUpdate,
)
from app.services import opportunity_rules


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------

def _filters(params: OpportunitySearchParams) -> dict[str, Any]:
    return {
        "text": params.q,
        "category_code": params.category,
        "skill_codes": tuple(params.skill),
        "work_mode": params.work_mode,
        "compensation_type": params.compensation_type,
        "organization_id": params.organization_id,
        "min_hours": params.min_hours,
        "max_hours": params.max_hours,
        "deadline_before": (
            to_db_datetime(params.deadline_before)
            if params.deadline_before
            else None
        ),
    }


def _page(
    session: Session,
    query: OpportunityQuery,
    params: OpportunitySearchParams,
) -> Page[OpportunityRead]:
    items, total = opportunity_repository.search(
        session,
        query,
        params.sort.value,
        params.limit,
        params.offset,
    )

    return Page[OpportunityRead](
        items=[OpportunityRead.model_validate(o) for o in items],
        total=total,
        limit=params.limit,
        offset=params.offset,
    )


def list_public(
    session: Session,
    params: OpportunitySearchParams,
) -> Page[OpportunityRead]:
    """Public browse: only open opportunities still accepting applications."""
    query = OpportunityQuery(
        statuses=(OpportunityStatus.OPEN,),
        deadline_after=utcnow(),
        **_filters(params),
    )
    return _page(session, query, params)


def list_mine(
    session: Session,
    creator: UserAccount,
    params: MyOpportunitySearchParams,
) -> Page[OpportunityRead]:
    """A creator's own opportunities in any status (drafts included)."""
    organization = user_repository.get_organization_of(
        session,
        creator.user_id,
    )

    if organization is None:
        return Page[OpportunityRead](
            items=[],
            total=0,
            limit=params.limit,
            offset=params.offset,
        )

    filters = _filters(params) | {
        "organization_id": organization.organization_id
    }

    query = OpportunityQuery(
        statuses=tuple(params.status),
        **filters,
    )

    return _page(session, query, params)


def _is_owner(
    opportunity: Opportunity,
    user: UserAccount | None,
) -> bool:
    return (
        user is not None
        and opportunity.organization.owner_user_id == user.user_id
    )


def get_visible(
    session: Session,
    opportunity_id: int,
    user: UserAccount | None,
) -> Opportunity:
    """Drafts are visible only to their owner; other statuses are public."""
    opportunity = opportunity_repository.get(session, opportunity_id)

    if opportunity is None or (
        opportunity.status == OpportunityStatus.DRAFT
        and not _is_owner(opportunity, user)
    ):
        raise NotFoundError(
            "Opportunity not found",
            code="OPPORTUNITY_NOT_FOUND",
        )

    return opportunity


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------

def _resolve_category(
    session: Session,
    code: str,
) -> OpportunityCategory:
    category = reference_repository.get_category_by_code(session, code)

    if category is None:
        raise UnprocessableError(
            f"Unknown category '{code}'",
            code="UNKNOWN_CATEGORY",
        )

    return category


def _resolve_skills(
    session: Session,
    codes: Sequence[str],
) -> list[Skill]:
    wanted = list(dict.fromkeys(codes))
    found = {
        skill.code: skill
        for skill in reference_repository.get_skills_by_codes(
            session,
            wanted,
        )
    }

    unknown = [code for code in wanted if code not in found]

    if unknown:
        raise UnprocessableError(
            "Unknown skill code(s)",
            code="UNKNOWN_SKILL",
            details={"unknown_skills": unknown},
        )

    return [found[code] for code in wanted]


def _get_owned_for_update(
    session: Session,
    opportunity_id: int,
    user: UserAccount,
) -> Opportunity:
    opportunity = opportunity_repository.get_for_update(
        session,
        opportunity_id,
    )

    if opportunity is None or (
        opportunity.status == OpportunityStatus.DRAFT
        and not _is_owner(opportunity, user)
    ):
        raise NotFoundError(
            "Opportunity not found",
            code="OPPORTUNITY_NOT_FOUND",
        )

    if not _is_owner(opportunity, user):
        raise ForbiddenError(
            "Only the owning creator can change this opportunity",
            code="NOT_OPPORTUNITY_OWNER",
        )

    return opportunity


_PLAIN_FIELDS = (
    "title",
    "description",
    "requirements",
    "location",
    "work_mode",
    "start_date",
    "end_date",
    "expected_hours",
    "compensation_type",
    "compensation_amount",
    "compensation_details",
    "applicant_limit",
    "working_conditions",
    "safety_information",
    "accessibility_details",
)


def _apply(
    session: Session,
    opportunity: Opportunity,
    data: OpportunityCreate | OpportunityUpdate,
) -> None:
    sent = data.model_fields_set

    for name in _PLAIN_FIELDS:
        if name in sent:
            setattr(opportunity, name, getattr(data, name))

    if "application_deadline" in sent:
        deadline = data.application_deadline
        opportunity.application_deadline = (
            to_db_datetime(deadline) if deadline else None
        )

    if "category" in sent and data.category is not None:
        opportunity.category = _resolve_category(
            session,
            data.category,
        )

    if "skills" in sent and data.skills is not None:
        opportunity.skills = _resolve_skills(
            session,
            data.skills,
        )

    if opportunity_rules.dates_out_of_order(opportunity):
        raise UnprocessableError(
            "end_date must be on or after start_date",
            code="INVALID_DATES",
        )


def create_draft(
    session: Session,
    creator: UserAccount,
    data: OpportunityCreate,
) -> Opportunity:
    organization = user_repository.get_organization_of(
        session,
        creator.user_id,
    )

    if organization is None:
        raise ConflictError(
            "Your account has no organization to post opportunities for",
            code="ORGANIZATION_REQUIRED",
        )

    opportunity = Opportunity(
        organization=organization,
        status=OpportunityStatus.DRAFT,
    )

    _apply(session, opportunity, data)
    opportunity_repository.add(session, opportunity)
    session.commit()

    return get_visible(
        session,
        opportunity.opportunity_id,
        creator,
    )


def update_draft(
    session: Session,
    creator: UserAccount,
    opportunity_id: int,
    data: OpportunityUpdate,
) -> Opportunity:
    opportunity = _get_owned_for_update(
        session,
        opportunity_id,
        creator,
    )

    if opportunity.status != OpportunityStatus.DRAFT:
        raise ConflictError(
            "Only draft opportunities can be edited",
            code="OPPORTUNITY_NOT_DRAFT",
        )

    _apply(session, opportunity, data)
    session.commit()
    session.refresh(opportunity)

    return opportunity


def delete_opportunity(
    session: Session,
    creator: UserAccount,
    opportunity_id: int,
) -> None:
    """Delete an opportunity owned by the authenticated creator."""
    opportunity = _get_owned_for_update(
        session,
        opportunity_id,
        creator,
    )

    session.delete(opportunity)
    session.commit()


def publish(
    session: Session,
    creator: UserAccount,
    opportunity_id: int,
    publisher: EventPublisher,
    correlation_id: str | None,
) -> Opportunity:
    """Validate mandatory disclosures, open the opportunity, commit, THEN publish the event."""
    opportunity = _get_owned_for_update(
        session,
        opportunity_id,
        creator,
    )

    if opportunity.status != OpportunityStatus.DRAFT:
        raise ConflictError(
            "Only draft opportunities can be published",
            code="OPPORTUNITY_NOT_DRAFT",
        )

    missing = opportunity_rules.missing_publish_fields(opportunity)

    if missing:
        raise UnprocessableError(
            "Opportunity is missing mandatory information",
            code="OPPORTUNITY_INCOMPLETE",
            details={"missing_fields": missing},
        )

    now = utcnow()

    if opportunity_rules.deadline_has_passed(opportunity, now):
        raise UnprocessableError(
            "application_deadline must be in the future",
            code="DEADLINE_PASSED",
        )

    opportunity.status = OpportunityStatus.OPEN
    opportunity.published_at = now

    payload = OpportunityCreatedPayload(
        opportunity_id=opportunity.opportunity_id,
        organization_id=opportunity.organization_id,
        title=opportunity.title,
        category_code=opportunity.category.code,
        application_deadline=as_utc(
            opportunity.application_deadline
        ),
        skill_codes=[skill.code for skill in opportunity.skills],
    )

    session.commit()
    session.refresh(opportunity)

    publisher.publish(
        payload,
        EventType.OPPORTUNITY_CREATED,
        correlation_id,
    )

    return opportunity
