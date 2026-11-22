"""Submitting work for an accepted application, and reading it back (ADR 0012).

Every rule is checked here first for a clear error, and again by the database
(trg_work_submission_bi, uq_work_submission_application), so a race ends in the same
409, never a 500.

Files follow ADR 0007: they are written first and the rows committed second, and if
anything after the first write fails, every file written so far is deleted. A crash
can orphan a file, never leave a row that points at nothing.
"""

import logging
import zipfile
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import BinaryIO

from grow8_common.events import EventType, WorkSubmittedPayload
from grow8_common.models import (
    Application,
    ApplicationStatus,
    OpportunityStatus,
    SubmissionAttachment,
    UserAccount,
    WorkSubmission,
)
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    PayloadTooLargeError,
    UnprocessableError,
    UnsupportedMediaTypeError,
)
from app.core.time import utcnow
from app.events.publisher import EventPublisher
from app.repositories import application_repository, opportunity_repository, submission_repository
from app.repositories.db_errors import duplicate_key, trigger_rule
from app.schemas.common import Page
from app.schemas.submission import ReceivedSubmissionParams, SubmissionCreate, SubmissionRead
from app.services import submission_rules
from app.services.submission_rules import FileType
from app.storage import FileStorage, StoredFileMissing, new_key

logger = logging.getLogger(__name__)

_CHUNK = 64 * 1024
_DUPLICATE_KEY = "uq_work_submission_application"


@dataclass(frozen=True)
class UploadedFile:
    """One file of the multipart request: its bytes and the name the client gave."""

    stream: BinaryIO
    file_name: str | None


@dataclass(frozen=True)
class AttachmentFile:
    """An open attachment to stream, with what the response headers need."""

    stream: BinaryIO
    file_name: str
    content_type: str
    size_bytes: int


@dataclass(frozen=True)
class _Checked:
    upload: UploadedFile
    file_type: FileType


def _now() -> datetime:
    # DATETIME columns have no fractional seconds; drop them rather than let MySQL round.
    return utcnow().replace(microsecond=0)


def _application_not_found() -> NotFoundError:
    return NotFoundError("Application not found", code="APPLICATION_NOT_FOUND")


def _submission_not_found() -> NotFoundError:
    return NotFoundError("Submission not found", code="SUBMISSION_NOT_FOUND")


def _attachment_not_found() -> NotFoundError:
    return NotFoundError("Attachment not found", code="ATTACHMENT_NOT_FOUND")


def _not_accepted() -> ConflictError:
    return ConflictError(
        "Work can only be submitted for an accepted application", code="APPLICATION_NOT_ACCEPTED"
    )


def _already_submitted() -> ConflictError:
    return ConflictError(
        "Work has already been submitted for this application", code="WORK_ALREADY_SUBMITTED"
    )


def _too_large() -> PayloadTooLargeError:
    return PayloadTooLargeError(
        f"Each file can be at most {submission_rules.MAX_FILE_BYTES // (1024 * 1024)} MB",
        code="ATTACHMENT_TOO_LARGE",
    )


def _can_see(application: Application, user: UserAccount) -> bool:
    """The applicant and the creator who owns the opportunity."""
    return (
        application.contributor_id == user.user_id
        or application.opportunity.organization.owner_user_id == user.user_id
    )


# ---------------------------------------------------------------------------
# Submitting
# ---------------------------------------------------------------------------


def _zip_entries(stream: BinaryIO) -> list[str]:
    """The entry names of a ZIP archive (DOCX/XLSX), or none if it can't be read."""
    try:
        with zipfile.ZipFile(stream) as archive:
            return archive.namelist()
    except (zipfile.BadZipFile, zipfile.LargeZipFile, OSError, ValueError, EOFError):
        return []


def _check_file(upload: UploadedFile) -> _Checked:
    """Recognise the file from its content and rewind it for saving."""
    head = upload.stream.read(submission_rules.SNIFF_BYTES)
    if not head:
        raise UnprocessableError("An uploaded file is empty", code="EMPTY_FILE")
    entries: list[str] = []
    if submission_rules.is_zip(head):
        upload.stream.seek(0)
        entries = _zip_entries(upload.stream)
    file_type = submission_rules.detect_type(head, upload.file_name, entries)
    if file_type is None:
        raise UnsupportedMediaTypeError(
            "Attachments must be PDF, PNG, JPEG, DOCX, XLSX, CSV or TXT files",
            code="UNSUPPORTED_FILE_TYPE",
        )
    upload.stream.seek(0)
    return _Checked(upload, file_type)


def _checked_chunks(stream: BinaryIO, sizes: list[int]) -> Iterator[bytes]:
    """Yield the file's bytes, stopping with ATTACHMENT_TOO_LARGE as soon as the total
    passes the limit, and record the size once the file is complete."""
    total = 0
    while chunk := stream.read(_CHUNK):
        total += len(chunk)
        if total > submission_rules.MAX_FILE_BYTES:
            raise _too_large()
        yield chunk
    sizes.append(total)


def _check_can_submit(session: Session, application: Application) -> None:
    """The rules, in the order a contributor would want to hear about them. The
    caller holds the application's row lock."""
    if application.status != ApplicationStatus.ACCEPTED:
        raise _not_accepted()
    if application_repository.has_submission(session, application.application_id):
        raise _already_submitted()
    # Shared lock, after the application's (the same order as deciding, ADR 0011): a
    # concurrent cancel waits for this submission, or this sees the cancel.
    if (
        opportunity_repository.lock_status_for_share(session, application.opportunity_id)
        == OpportunityStatus.CANCELLED
    ):
        raise ConflictError(
            "This opportunity was cancelled, so work can't be submitted for it",
            code="OPPORTUNITY_CANCELLED",
        )


def _conflict_from_db(exc: DBAPIError) -> ConflictError | None:
    if trigger_rule(exc) == "submission_requires_accepted":
        return _not_accepted()
    if duplicate_key(exc, _DUPLICATE_KEY):
        return _already_submitted()
    return None


def _save_and_insert(
    session: Session,
    storage: FileStorage,
    application: Application,
    data: SubmissionCreate,
    checked: Sequence[_Checked],
    saved_keys: list[str],
) -> WorkSubmission:
    now = _now()
    submission = WorkSubmission(
        application_id=application.application_id,
        description=data.description,
        hours_claimed=data.hours_claimed,
        submitted_at=now,
    )
    for item in checked:
        key = new_key("submissions")
        sizes: list[int] = []
        storage.save(key, _checked_chunks(item.upload.stream, sizes))
        saved_keys.append(key)
        submission.attachments.append(
            SubmissionAttachment(
                file_name=submission_rules.clean_file_name(item.upload.file_name, item.file_type),
                content_type=item.file_type.content_type,
                size_bytes=sizes[0],
                storage_key=key,
                uploaded_at=now,
            )
        )
    submission_repository.add(session, submission)
    session.commit()
    return submission


def submit(
    session: Session,
    storage: FileStorage,
    contributor: UserAccount,
    application_id: int,
    data: SubmissionCreate,
    files: Sequence[UploadedFile],
    publisher: EventPublisher,
    correlation_id: str | None,
) -> SubmissionRead:
    """Submit your work for your accepted application, with up to MAX_FILES files.
    The owning creator is told it is waiting for verification."""
    if len(files) > submission_rules.MAX_FILES:
        raise UnprocessableError(
            f"A submission can have at most {submission_rules.MAX_FILES} files",
            code="TOO_MANY_FILES",
        )

    application = application_repository.get_for_update(session, application_id)
    if application is None or application.contributor_id != contributor.user_id:
        raise _application_not_found()
    _check_can_submit(session, application)
    checked = [_check_file(f) for f in files]

    saved_keys: list[str] = []
    try:
        submission = _save_and_insert(session, storage, application, data, checked, saved_keys)
    except BaseException as exc:
        session.rollback()
        for key in saved_keys:
            _delete_quietly(storage, key)
        conflict = _conflict_from_db(exc) if isinstance(exc, DBAPIError) else None
        if conflict is None:
            raise
        raise conflict from exc

    publisher.publish(
        WorkSubmittedPayload(
            submission_id=submission.submission_id,
            application_id=application.application_id,
            opportunity_id=application.opportunity_id,
            organization_id=application.opportunity.organization_id,
            opportunity_title=application.opportunity.title,
            contributor_id=contributor.user_id,
            contributor_name=contributor.full_name,
            hours_claimed=submission.hours_claimed,
            attachment_count=len(submission.attachments),
        ),
        EventType.WORK_SUBMITTED,
        correlation_id,
    )
    return SubmissionRead.from_model(submission)


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


def get_for_application(session: Session, user: UserAccount, application_id: int) -> SubmissionRead:
    """The submission for an application, for the applicant or the owning creator. To
    anyone else the application doesn't exist."""
    application = application_repository.get(session, application_id)
    if application is None or not _can_see(application, user):
        raise _application_not_found()
    submission = submission_repository.get_for_application(session, application_id)
    if submission is None:
        raise NotFoundError("No work has been submitted yet", code="SUBMISSION_NOT_FOUND")
    return SubmissionRead.from_model(submission)


def get(session: Session, user: UserAccount, submission_id: int) -> SubmissionRead:
    """A submission with its verification, for the applicant or the owning creator. To
    anyone else it doesn't exist (ADR 0013)."""
    submission = submission_repository.get(session, submission_id)
    if submission is None or not _can_see(submission.application, user):
        raise _submission_not_found()
    return SubmissionRead.from_model(submission)


def list_received(
    session: Session, creator: UserAccount, params: ReceivedSubmissionParams
) -> Page[SubmissionRead]:
    """The creator's review queue: submissions to every opportunity they own, oldest
    first. An `opportunity_id` that isn't theirs simply matches nothing."""
    items, total = submission_repository.list_received(
        session,
        creator.user_id,
        params.opportunity_id,
        [s.value for s in params.status],
        params.limit,
        params.offset,
    )
    return Page[SubmissionRead](
        items=[SubmissionRead.from_model(s) for s in items],
        total=total,
        limit=params.limit,
        offset=params.offset,
    )


def open_attachment(
    session: Session,
    storage: FileStorage,
    user: UserAccount,
    submission_id: int,
    attachment_id: int,
) -> AttachmentFile:
    """An attachment to download, for the applicant or the owning creator. Anything
    they can't see, or that doesn't exist, is the same 404."""
    submission = submission_repository.get(session, submission_id)
    if submission is None or not _can_see(submission.application, user):
        raise _attachment_not_found()
    attachment = submission_repository.get_attachment(session, submission_id, attachment_id)
    if attachment is None:
        raise _attachment_not_found()
    try:
        stream = storage.open(attachment.storage_key)
    # ValueError: a key the store can't hold, e.g. the dev seed's placeholder keys
    except (StoredFileMissing, ValueError):
        logger.error(
            "attachment_id=%s points at a missing or invalid file key=%s",
            attachment.attachment_id,
            attachment.storage_key,
        )
        raise _attachment_not_found() from None
    return AttachmentFile(
        stream, attachment.file_name, attachment.content_type, attachment.size_bytes
    )


def _delete_quietly(storage: FileStorage, key: str) -> None:
    try:
        storage.delete(key)
    except OSError:
        logger.warning("could not delete file key=%s after a failed submission", key)
