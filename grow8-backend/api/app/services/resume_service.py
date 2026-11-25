"""A contributor's optional resume (ADR 0008), stored through FileStorage (ADR 0007).

Order of operations keeps MySQL honest: the file is written first, the row committed
second, and a replaced file deleted only after the commit. A crash can orphan a file,
never leave a row that points at nothing.
"""

import logging
from collections.abc import Iterator
from dataclasses import dataclass
from typing import BinaryIO

from grow8_common.models import ContributorResume, UserAccount
from sqlalchemy.orm import Session

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    PayloadTooLargeError,
    UnprocessableError,
    UnsupportedMediaTypeError,
)
from app.core.time import utcnow
from app.repositories import application_repository, resume_repository
from app.services.file_names import clean_display_name
from app.storage import FileStorage, StoredFileMissing, new_key

logger = logging.getLogger(__name__)

MAX_BYTES = 10 * 1024 * 1024  # 10 MB
PDF_SIGNATURE = b"%PDF-"
CONTENT_TYPE = "application/pdf"
_CHUNK = 64 * 1024
_DEFAULT_NAME = "resume.pdf"


@dataclass(frozen=True)
class ResumeFile:
    """An open resume to stream, with what the response headers need."""

    stream: BinaryIO
    file_name: str
    content_type: str
    size_bytes: int


def too_large() -> PayloadTooLargeError:
    return PayloadTooLargeError(
        f"A resume can be at most {MAX_BYTES // (1024 * 1024)} MB", code="RESUME_TOO_LARGE"
    )


def _not_found() -> NotFoundError:
    return NotFoundError("Resume not found", code="RESUME_NOT_FOUND")


def clean_file_name(name: str | None) -> str:
    """A display name only (never a path): last path segment, no control characters,
    at most 255 characters, ending in .pdf."""
    return clean_display_name(name, _DEFAULT_NAME, (".pdf",))


def _checked_chunks(head: bytes, upload: BinaryIO, counter: list[int]) -> Iterator[bytes]:
    """Yield the upload's bytes (starting with the already-read `head`), stopping with
    RESUME_TOO_LARGE as soon as the total passes MAX_BYTES."""
    total = len(head)
    yield head
    while chunk := upload.read(_CHUNK):
        total += len(chunk)
        if total > MAX_BYTES:
            raise too_large()
        yield chunk
    counter.append(total)


def upload(
    session: Session,
    storage: FileStorage,
    contributor: UserAccount,
    upload_file: BinaryIO,
    file_name: str | None,
) -> ContributorResume:
    """Create or replace the caller's resume."""
    head = upload_file.read(len(PDF_SIGNATURE))
    if not head:
        raise UnprocessableError("The uploaded file is empty", code="EMPTY_FILE")
    if head != PDF_SIGNATURE:
        raise UnsupportedMediaTypeError("A resume must be a PDF file", code="UNSUPPORTED_FILE_TYPE")

    if resume_repository.lock_profile(session, contributor.user_id) is None:
        raise ConflictError(
            "Save your profile first",
            code="CONTRIBUTOR_PROFILE_REQUIRED",
        )

    key = new_key("resumes")
    size: list[int] = []
    storage.save(key, _checked_chunks(head, upload_file, size))

    resume = resume_repository.get(session, contributor.user_id)
    replaced_key = resume.storage_key if resume else None
    if resume is None:
        resume = ContributorResume(user_id=contributor.user_id)
        resume_repository.add(session, resume)
    resume.file_name = clean_file_name(file_name)
    resume.content_type = CONTENT_TYPE
    resume.size_bytes = size[0]
    resume.storage_key = key
    resume.uploaded_at = utcnow().replace(microsecond=0)
    try:
        session.commit()
    except Exception:
        session.rollback()
        storage.delete(key)
        raise

    if replaced_key:
        delete_quietly(storage, replaced_key)
    return resume


def store_application_resume(
    storage: FileStorage, upload_file: BinaryIO, file_name: str | None
) -> tuple[str, str, str, int]:
    """Store an application-only resume without changing the contributor profile."""
    head = upload_file.read(len(PDF_SIGNATURE))
    if not head:
        raise UnprocessableError("The uploaded file is empty", code="EMPTY_FILE")
    if head != PDF_SIGNATURE:
        raise UnsupportedMediaTypeError("A resume must be a PDF file", code="UNSUPPORTED_FILE_TYPE")
    key = new_key("applicationresumes")
    size: list[int] = []
    storage.save(key, _checked_chunks(head, upload_file, size))
    return key, clean_file_name(file_name), CONTENT_TYPE, size[0]


def get_mine(session: Session, contributor: UserAccount) -> ContributorResume:
    resume = resume_repository.get(session, contributor.user_id)
    if resume is None:
        raise _not_found()
    return resume


def delete_mine(session: Session, storage: FileStorage, contributor: UserAccount) -> None:
    if resume_repository.lock_profile(session, contributor.user_id) is None:
        raise _not_found()
    resume = resume_repository.get(session, contributor.user_id)
    if resume is None:
        raise _not_found()
    key = resume.storage_key
    resume_repository.delete(session, resume)
    session.commit()
    delete_quietly(storage, key)


def open_mine(session: Session, storage: FileStorage, contributor: UserAccount) -> ResumeFile:
    return _open(storage, get_mine(session, contributor))


def open_for_application(
    session: Session, storage: FileStorage, user: UserAccount, application_id: int
) -> ResumeFile:
    """The resume saved with the application, for its creator or applicant only."""
    application = application_repository.get(session, application_id)
    if application is None or (
        application.contributor_id != user.user_id
        and application.opportunity.organization.owner_user_id != user.user_id
    ):
        raise NotFoundError("Application not found", code="APPLICATION_NOT_FOUND")
    if application.resume_storage_key:
        try:
            stream = storage.open(application.resume_storage_key)
        except StoredFileMissing:
            raise _not_found() from None
        return ResumeFile(
            stream,
            application.resume_file_name or "resume.pdf",
            application.resume_content_type or CONTENT_TYPE,
            application.resume_size_bytes or 0,
        )
    resume = resume_repository.get(session, application.contributor_id)
    if resume is None:
        raise _not_found()
    return _open(storage, resume)


def _open(storage: FileStorage, resume: ContributorResume) -> ResumeFile:
    try:
        stream = storage.open(resume.storage_key)
    except StoredFileMissing:
        logger.error(
            "resume row for user_id=%s points at a missing file key=%s",
            resume.user_id,
            resume.storage_key,
        )
        raise _not_found() from None
    return ResumeFile(stream, resume.file_name, resume.content_type, resume.size_bytes)


def delete_quietly(storage: FileStorage, key: str) -> None:
    """Delete a stored file that no row points to any more; log instead of failing."""
    try:
        storage.delete(key)
    except OSError:
        logger.warning("could not delete replaced file key=%s; it is now an orphan", key)
