"""Applying, deciding and withdrawing (ADR 0006).

Every rule is checked here first for a clear error, and again by the database
triggers, so a race the checks can't see still ends in the same 409, never a 500.
"""

import logging
from collections.abc import Callable
from datetime import datetime
from typing import BinaryIO

from grow8_common.events import (
    ApplicationDecidedPayload,
    ApplicationSubmittedPayload,
    ApplicationWithdrawnPayload,
    EventType,
)
from grow8_common.models import (
    Application,
    ApplicationStatus,
    Opportunity,
    OpportunityStatus,
    UserAccount,
)
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.time import utcnow
from app.events.publisher import EventPublisher
from app.repositories import (
    application_repository,
    opportunity_repository,
    resume_repository,
    user_repository,
)
from app.repositories.db_errors import duplicate_key, trigger_rule
from app.schemas.application import (
    ApplicationCreate,
    ApplicationListParams,
    ApplicationRead,
    Decision,
    ReceivedApplicationParams,
)
from app.schemas.common import Page
from app.services import application_rules, resume_service
from app.storage import FileStorage, StoredFileMissing, new_key

logger = logging.getLogger(__name__)

_MESSAGES = {
    "OPPORTUNITY_NOT_OPEN": "This opportunity is not open for applications",
    "APPLICATION_DEADLINE_PASSED": "The application deadline has passed",
    "APPLICANT_LIMIT_REACHED": "This opportunity has no places left",
}

# Trigger rule name (db/init/001_schema.sql) -> API error code.
_TRIGGER_CODES = {
    "application_closed": "OPPORTUNITY_NOT_OPEN",
    "application_deadline_passed": "APPLICATION_DEADLINE_PASSED",
    "applicant_limit_reached": "APPLICANT_LIMIT_REACHED",
    "submission_requires_accepted": "WORK_ALREADY_SUBMITTED",
}
_DUPLICATE_KEY = "uq_application_contributor_opportunity"


def _now() -> datetime:
    # DATETIME columns have no fractional seconds and MySQL rounds them, which could
    # date a row up to half a second in the future; drop them instead.
    return utcnow().replace(microsecond=0)


def _not_found() -> NotFoundError:
    return NotFoundError("Application not found", code="APPLICATION_NOT_FOUND")


def _owns(opportunity: Opportunity, user: UserAccount) -> bool:
    return opportunity.organization.owner_user_id == user.user_id


def _conflict_from_db(exc: DBAPIError) -> ConflictError | None:
    code = _TRIGGER_CODES.get(trigger_rule(exc) or "")
    if code == "WORK_ALREADY_SUBMITTED":
        return ConflictError("Work has already been submitted for this application", code=code)
    if code:
        return ConflictError(_MESSAGES[code], code=code)
    if duplicate_key(exc, _DUPLICATE_KEY):
        return ConflictError(
            "You have already applied to this opportunity", code="APPLICATION_DUPLICATE"
        )
    return None


def _commit(session: Session) -> None:
    """Commit, turning a broken database rule into the matching 409."""
    try:
        session.commit()
    except DBAPIError as exc:
        session.rollback()
        conflict = _conflict_from_db(exc)
        if conflict is None:
            raise
        raise conflict from exc


def _page(items: list[Application], total: int, params: ApplicationListParams) -> Page:
    return Page[ApplicationRead](
        items=[ApplicationRead.from_model(a) for a in items],
        total=total,
        limit=params.limit,
        offset=params.offset,
    )


# ---------------------------------------------------------------------------
# Contributor actions
# ---------------------------------------------------------------------------


def apply(
    session: Session,
    contributor: UserAccount,
    opportunity_id: int,
    data: ApplicationCreate,
    publisher: EventPublisher,
    correlation_id: str | None,
    storage: FileStorage | None = None,
    resume_upload: BinaryIO | None = None,
    resume_file_name: str | None = None,
) -> ApplicationRead:
    """Apply to an open opportunity. The opportunity row stays locked until commit,
    so two people can't both take its last place."""
    profile = user_repository.get_contributor_profile(session, contributor.user_id)
    if profile is None:
        raise ConflictError(
            "Save your profile first",
            code="CONTRIBUTOR_PROFILE_REQUIRED",
        )

    opportunity = opportunity_repository.get_for_update(session, opportunity_id)
    if opportunity is None or opportunity.status == OpportunityStatus.DRAFT:
        raise NotFoundError("Opportunity not found", code="OPPORTUNITY_NOT_FOUND")

    existing = application_repository.find(session, contributor.user_id, opportunity_id)
    if existing is not None:
        if (
            existing.status == ApplicationStatus.WITHDRAWN
            and not application_repository.has_submission(session, existing.application_id)
        ):
            # Reuse the unique application row, preserving its id and any related
            # history while allowing a contributor to apply again after withdrawal.
            now = _now()
            refusal = application_rules.apply_refusal(
                opportunity.status,
                opportunity.application_deadline,
                opportunity.applicant_limit,
                application_repository.count_active(session, opportunity_id),
                now,
            )
            if refusal:
                raise ConflictError(_MESSAGES[refusal], code=refusal)
            existing.status = ApplicationStatus.PENDING
            existing.motivation = data.motivation
            existing.application_details = data.application_details
            existing.submitted_at = now
            existing.decided_at = None
            replaced_key = existing.resume_storage_key
            new_file = _snapshot_resume(
                session, storage, contributor.user_id, existing, resume_upload, resume_file_name
            )
            _save_with_file(session, storage, new_file, lambda: None)
            if storage is not None and replaced_key and replaced_key != new_file:
                resume_service.delete_quietly(storage, replaced_key)
            publisher.publish(
                ApplicationSubmittedPayload(
                    application_id=existing.application_id,
                    opportunity_id=opportunity.opportunity_id,
                    organization_id=opportunity.organization_id,
                    opportunity_title=opportunity.title,
                    contributor_id=contributor.user_id,
                    contributor_name=contributor.full_name,
                ),
                EventType.APPLICATION_SUBMITTED,
                correlation_id,
            )
            return ApplicationRead.from_model(existing)
        raise ConflictError(
            "You have already applied to this opportunity",
            code="APPLICATION_DUPLICATE",
            details={"application_id": existing.application_id},
        )

    now = _now()
    refusal = application_rules.apply_refusal(
        opportunity.status,
        opportunity.application_deadline,
        opportunity.applicant_limit,
        application_repository.count_active(session, opportunity_id),
        now,
    )
    if refusal:
        raise ConflictError(_MESSAGES[refusal], code=refusal)

    application = Application(
        opportunity=opportunity,
        contributor=profile,
        status=ApplicationStatus.PENDING,
        motivation=data.motivation,
        application_details=data.application_details,
        submitted_at=now,
    )
    new_file = _snapshot_resume(
        session, storage, contributor.user_id, application, resume_upload, resume_file_name
    )
    _save_with_file(session, storage, new_file, lambda: _add(session, application))

    publisher.publish(
        ApplicationSubmittedPayload(
            application_id=application.application_id,
            opportunity_id=opportunity.opportunity_id,
            organization_id=opportunity.organization_id,
            opportunity_title=opportunity.title,
            contributor_id=contributor.user_id,
            contributor_name=contributor.full_name,
        ),
        EventType.APPLICATION_SUBMITTED,
        correlation_id,
    )
    return ApplicationRead.from_model(application)


def _add(session: Session, application: Application) -> None:
    try:
        application_repository.add(session, application)
    except DBAPIError as exc:
        session.rollback()
        conflict = _conflict_from_db(exc)
        if conflict is None:
            raise
        raise conflict from exc


def _save_with_file(
    session: Session,
    storage: FileStorage | None,
    new_file: str | None,
    write: Callable[[], None],
) -> None:
    """Write and commit the application. The resume copy was stored first (ADR 0007), so
    if the database refuses the row, delete it again rather than leave an orphan (#48)."""
    try:
        write()
        _commit(session)
    except BaseException:
        if storage is not None and new_file:
            resume_service.delete_quietly(storage, new_file)
        raise


def _snapshot_resume(
    session: Session,
    storage: FileStorage | None,
    contributor_id: int,
    application: Application,
    resume_upload: BinaryIO | None = None,
    resume_file_name: str | None = None,
) -> str | None:
    """Store the resume sent with the application, or a copy of the profile resume, and
    point the application at it (ADR 0020). Returns the new file's key, if any."""
    if storage is None:
        return None
    if resume_upload is not None:
        key, name, content_type, size = resume_service.store_application_resume(
            storage, resume_upload, resume_file_name
        )
        application.resume_storage_key = key
        application.resume_file_name = name
        application.resume_content_type = content_type
        application.resume_size_bytes = size
        return key
    resume = resume_repository.get(session, contributor_id)
    try:
        source = storage.open(resume.storage_key) if resume else None
    except StoredFileMissing:
        logger.warning(
            "profile resume file missing key=%s; applying without it", resume.storage_key
        )
        source = None
    if resume is None or source is None:
        application.resume_file_name = None
        application.resume_content_type = None
        application.resume_size_bytes = None
        application.resume_storage_key = None
        return None
    key = new_key("applicationresumes")
    try:
        storage.save(key, iter(lambda: source.read(64 * 1024), b""))
    finally:
        source.close()
    application.resume_file_name = resume.file_name
    application.resume_content_type = resume.content_type
    application.resume_size_bytes = resume.size_bytes
    application.resume_storage_key = key
    return key


def list_mine(
    session: Session, contributor: UserAccount, params: ApplicationListParams
) -> Page[ApplicationRead]:
    items, total = application_repository.list_for_contributor(
        session,
        contributor.user_id,
        params.status,
        params.limit,
        params.offset,
        params.opportunity_id,
    )
    return _page(list(items), total, params)


def withdraw(
    session: Session,
    contributor: UserAccount,
    application_id: int,
    publisher: EventPublisher,
    correlation_id: str | None,
) -> ApplicationRead:
    """Withdraw your own pending or accepted application, unless work was submitted.
    Withdrawing frees the place it held, and the owning creator is told."""
    application = application_repository.get_for_update(session, application_id)
    if application is None or application.contributor_id != contributor.user_id:
        raise _not_found()
    if not application_rules.can_withdraw(application.status):
        raise ConflictError(
            f"A {application.status.value} application cannot be withdrawn",
            code="APPLICATION_NOT_ACTIVE",
        )
    if application_repository.has_submission(session, application_id):
        raise ConflictError(
            "Work has already been submitted for this application",
            code="WORK_ALREADY_SUBMITTED",
        )

    previous_status = application.status
    application.status = ApplicationStatus.WITHDRAWN
    _commit(session)

    publisher.publish(
        ApplicationWithdrawnPayload(
            application_id=application.application_id,
            opportunity_id=application.opportunity_id,
            organization_id=application.opportunity.organization_id,
            opportunity_title=application.opportunity.title,
            contributor_id=contributor.user_id,
            contributor_name=contributor.full_name,
            previous_status=previous_status.value,
        ),
        EventType.APPLICATION_WITHDRAWN,
        correlation_id,
    )
    return ApplicationRead.from_model(application)


# ---------------------------------------------------------------------------
# Creator actions
# ---------------------------------------------------------------------------


def list_for_opportunity(
    session: Session,
    creator: UserAccount,
    opportunity_id: int,
    params: ApplicationListParams,
) -> Page[ApplicationRead]:
    """Applications to an opportunity the creator owns."""
    opportunity = opportunity_repository.get(session, opportunity_id)
    if opportunity is None or (
        opportunity.status == OpportunityStatus.DRAFT and not _owns(opportunity, creator)
    ):
        raise NotFoundError("Opportunity not found", code="OPPORTUNITY_NOT_FOUND")
    if not _owns(opportunity, creator):
        raise ForbiddenError(
            "Only the owning creator can see this opportunity's applications",
            code="NOT_OPPORTUNITY_OWNER",
        )
    items, total = application_repository.list_for_opportunity(
        session, opportunity_id, params.status, params.limit, params.offset
    )
    return _page(list(items), total, params)


def list_received(
    session: Session, creator: UserAccount, params: ReceivedApplicationParams
) -> Page[ApplicationRead]:
    """Applications to every opportunity the creator owns, newest first. An
    `opportunity_id` that isn't theirs simply matches nothing."""
    items, total = application_repository.list_received(
        session,
        creator.user_id,
        params.opportunity_id,
        params.status,
        params.limit,
        params.offset,
    )
    return _page(list(items), total, params)


def decide(
    session: Session,
    creator: UserAccount,
    application_id: int,
    decision: Decision,
    publisher: EventPublisher,
    correlation_id: str | None,
) -> ApplicationRead:
    """Accept or reject a pending application to an opportunity you own. Each one is
    decided once; deciding is allowed after the deadline or once the opportunity closes,
    but not once it is cancelled (ADR 0011)."""
    application = application_repository.get_for_update(session, application_id)
    if application is None or not _owns(application.opportunity, creator):
        raise _not_found()
    if not application_rules.can_decide(application.status):
        raise ConflictError(
            f"Only pending applications can be decided (this one is {application.status.value})",
            code="APPLICATION_NOT_PENDING",
        )
    # Shared lock: a concurrent cancel waits for this decision, or this sees it.
    if (
        opportunity_repository.lock_status_for_share(session, application.opportunity_id)
        == OpportunityStatus.CANCELLED
    ):
        raise ConflictError(
            "This opportunity was cancelled, so its applications can't be decided",
            code="OPPORTUNITY_CANCELLED",
        )

    application.status = ApplicationStatus(decision.value)
    application.decided_at = _now()
    _commit(session)

    publisher.publish(
        ApplicationDecidedPayload(
            application_id=application.application_id,
            opportunity_id=application.opportunity_id,
            opportunity_title=application.opportunity.title,
            contributor_id=application.contributor_id,
            decision=decision.value,
        ),
        EventType.APPLICATION_DECIDED,
        correlation_id,
    )
    return ApplicationRead.from_model(application)


# ---------------------------------------------------------------------------
# Either party
# ---------------------------------------------------------------------------


def get_visible(session: Session, user: UserAccount, application_id: int) -> ApplicationRead:
    """The applicant and the owning creator can see an application; to everyone else
    it doesn't exist, so ids can't be probed."""
    application = application_repository.get(session, application_id)
    if application is None or (
        application.contributor_id != user.user_id and not _owns(application.opportunity, user)
    ):
        raise _not_found()
    return ApplicationRead.from_model(application)
