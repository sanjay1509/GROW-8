from collections.abc import Sequence

from grow8_common.models import (
    Application,
    ApplicationStatus,
    ContributorProfile,
    CreatorOrganization,
    Opportunity,
    WorkSubmission,
)
from sqlalchemy import ColumnElement, Select, exists, func, select
from sqlalchemy.orm import Session, joinedload, selectinload

ACTIVE_STATUSES = (ApplicationStatus.PENDING, ApplicationStatus.ACCEPTED)

_EAGER = (
    joinedload(Application.opportunity).joinedload(Opportunity.organization),
    joinedload(Application.contributor).options(
        joinedload(ContributorProfile.user),
        selectinload(ContributorProfile.skills),
        selectinload(ContributorProfile.resume),
    ),
    selectinload(Application.submission).selectinload(WorkSubmission.verification),
)


def _by_id(application_id: int) -> Select[tuple[Application]]:
    return select(Application).options(*_EAGER).where(Application.application_id == application_id)


def get(session: Session, application_id: int) -> Application | None:
    return session.scalars(_by_id(application_id)).unique().first()


def get_for_update(session: Session, application_id: int) -> Application | None:
    """Load and row-lock the application until the transaction ends."""
    stmt = _by_id(application_id).with_for_update(of=Application)
    return session.scalars(stmt).unique().first()


def find(session: Session, contributor_id: int, opportunity_id: int) -> Application | None:
    stmt = select(Application).where(
        Application.contributor_id == contributor_id,
        Application.opportunity_id == opportunity_id,
    )
    return session.scalars(stmt).first()


def count_active(session: Session, opportunity_id: int) -> int:
    """Pending + accepted applications: the ones that hold a place.

    A locking read (FOR SHARE), so it sees the latest committed rows rather than the
    transaction's snapshot; call it while holding the opportunity's row lock."""
    stmt = (
        select(func.count(Application.application_id))
        .where(
            Application.opportunity_id == opportunity_id,
            Application.status.in_(ACTIVE_STATUSES),
        )
        .with_for_update(read=True)
    )
    return session.scalar(stmt) or 0


def has_submission(session: Session, application_id: int) -> bool:
    stmt = select(exists().where(WorkSubmission.application_id == application_id))
    return bool(session.scalar(stmt))


def opportunity_has_submission(session: Session, opportunity_id: int) -> bool:
    """Whether work was submitted for any application to the opportunity."""
    stmt = select(
        exists()
        .where(WorkSubmission.application_id == Application.application_id)
        .where(Application.opportunity_id == opportunity_id)
    )
    return bool(session.scalar(stmt))


def add(session: Session, application: Application) -> Application:
    session.add(application)
    session.flush()
    return application


def _page(
    session: Session,
    conds: list[ColumnElement[bool]],
    limit: int,
    offset: int,
    owner_user_id: int | None = None,
) -> tuple[Sequence[Application], int]:
    """One page plus the total. With `owner_user_id`, only applications to
    opportunities of organizations that user owns."""
    count = select(func.count(Application.application_id))
    stmt = select(Application).options(*_EAGER)
    if owner_user_id is not None:
        owned = (
            Application.opportunity_id.in_(
                select(Opportunity.opportunity_id)
                .join(CreatorOrganization)
                .where(CreatorOrganization.owner_user_id == owner_user_id)
            ),
        )
        count, stmt = count.where(*owned), stmt.where(*owned)
    total = session.scalar(count.where(*conds)) or 0
    stmt = (
        stmt.where(*conds)
        .order_by(Application.submitted_at.desc(), Application.application_id.desc())
        .limit(limit)
        .offset(offset)
    )
    return session.scalars(stmt).unique().all(), total


def list_for_contributor(
    session: Session,
    contributor_id: int,
    statuses: Sequence[ApplicationStatus],
    limit: int,
    offset: int,
    opportunity_id: int | None = None,
) -> tuple[Sequence[Application], int]:
    """One page of a contributor's applications, newest first, plus the total."""
    conds = [Application.contributor_id == contributor_id]
    if opportunity_id is not None:
        conds.append(Application.opportunity_id == opportunity_id)
    if statuses:
        conds.append(Application.status.in_(statuses))
    return _page(session, conds, limit, offset)


def list_for_opportunity(
    session: Session,
    opportunity_id: int,
    statuses: Sequence[ApplicationStatus],
    limit: int,
    offset: int,
) -> tuple[Sequence[Application], int]:
    """One page of an opportunity's applications, newest first, plus the total."""
    conds = [Application.opportunity_id == opportunity_id]
    if statuses:
        conds.append(Application.status.in_(statuses))
    return _page(session, conds, limit, offset)


def list_received(
    session: Session,
    owner_user_id: int,
    opportunity_id: int | None,
    statuses: Sequence[ApplicationStatus],
    limit: int,
    offset: int,
) -> tuple[Sequence[Application], int]:
    """One page of applications to every opportunity the creator owns (optionally just
    one of them), newest first, plus the total."""
    conds: list[ColumnElement[bool]] = []
    if opportunity_id is not None:
        conds.append(Application.opportunity_id == opportunity_id)
    if statuses:
        conds.append(Application.status.in_(statuses))
    return _page(session, conds, limit, offset, owner_user_id=owner_user_id)
