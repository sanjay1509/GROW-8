"""submission_service against the seeded test database and a temporary file store
(ADR 0012). The HTTP layer is tested separately once the endpoints exist.

Seeded: opportunity 1 is open and belongs to organization 1, owned by Priya Nair
(user 2); Daniel Okafor (user 3) owns organization 2. Alex Chen is user 5, Jordan Lee
user 6. The tests add their own applications, since 002_seed.sql has none.
"""

import io
import zipfile
from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path

import pymysql
import pytest
from grow8_common.db import get_sessionmaker
from grow8_common.events import EventType, WorkSubmittedPayload
from grow8_common.models import UserAccount, WorkSubmission
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.schemas.submission import SubmissionCreate
from app.services import submission_rules, submission_service
from app.services.submission_service import UploadedFile
from app.storage import LocalFileStorage
from tests.fakes import FakePublisher

PDF = b"%PDF-1.7\n" + b"x" * 100
CSV = b"date,hours\n2026-11-01,3.5\n"
EXE = b"MZ\x90\x00\x03\x00\x00\x00"


def _docx() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<document/>")
    return buffer.getvalue()


def _file(data: bytes, name: str | None) -> UploadedFile:
    return UploadedFile(io.BytesIO(data), name)


def _application(conn: pymysql.Connection, contributor_id: int, status: str = "accepted") -> int:
    decided = None if status == "pending" else "2026-10-14 12:00:00"
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO application (opportunity_id, contributor_id, status, submitted_at, "
            "decided_at) VALUES (1, %s, %s, '2026-10-14 10:00:00', %s)",
            (contributor_id, status, decided),
        )
        return cur.lastrowid


@pytest.fixture
def session(seeded_db: pymysql.Connection) -> Iterator[Session]:
    with get_sessionmaker()() as s:
        yield s


@pytest.fixture
def storage(tmp_path: Path) -> LocalFileStorage:
    return LocalFileStorage(tmp_path / "storage")


@pytest.fixture
def publisher() -> FakePublisher:
    return FakePublisher()


def _stored_files(tmp_path: Path) -> list[Path]:
    return [p for p in (tmp_path / "storage").rglob("*") if p.is_file()]


def _user(session: Session, user_id: int) -> UserAccount:
    user = session.get(UserAccount, user_id)
    assert user is not None
    return user


def _submit(
    session: Session,
    storage: LocalFileStorage,
    publisher: FakePublisher,
    application_id: int,
    files: list[UploadedFile] = (),
    contributor_id: int = 5,
):
    return submission_service.submit(
        session,
        storage,
        _user(session, contributor_id),
        application_id,
        SubmissionCreate(description="Typed up 40 recipes.", hours_claimed=Decimal("6.50")),
        list(files),
        publisher,
        "req-1",
    )


def _code(exc_info: pytest.ExceptionInfo[AppError]) -> tuple[int, str]:
    return exc_info.value.status_code, exc_info.value.code


def _count_submissions(session: Session) -> int:
    session.rollback()  # end the transaction so the count sees committed rows
    return session.scalar(select(func.count(WorkSubmission.submission_id))) or 0


# ---------------------------------------------------------------------------
# Submitting
# ---------------------------------------------------------------------------


def test_submits_work_with_files_and_publishes_the_event(
    seeded_db, session, storage, publisher, tmp_path
) -> None:
    application_id = _application(seeded_db, 5)

    result = _submit(
        session,
        storage,
        publisher,
        application_id,
        [_file(PDF, "sheets.pdf"), _file(_docx(), "notes"), _file(CSV, "hours.csv")],
    )

    assert result.application_id == application_id
    assert result.hours_claimed == Decimal("6.50")
    assert [(a.file_name, a.content_type, a.size_bytes) for a in result.attachments] == [
        ("sheets.pdf", "application/pdf", len(PDF)),
        ("notes.docx", submission_rules.DOCX.content_type, len(_docx())),
        ("hours.csv", "text/csv", len(CSV)),
    ]
    assert sorted(p.read_bytes() for p in _stored_files(tmp_path)) == sorted([PDF, _docx(), CSV])

    [event] = publisher.events
    assert event.event_type == EventType.WORK_SUBMITTED
    assert event.correlation_id == "req-1"
    payload = WorkSubmittedPayload.model_validate(event.payload)
    assert payload.submission_id == result.submission_id
    assert (payload.opportunity_id, payload.organization_id) == (1, 1)
    assert (payload.contributor_id, payload.contributor_name) == (5, "Alex Chen")
    assert (payload.hours_claimed, payload.attachment_count) == (Decimal("6.50"), 3)


def test_files_are_optional(seeded_db, session, storage, publisher) -> None:
    result = _submit(session, storage, publisher, _application(seeded_db, 5))
    assert result.attachments == []
    assert len(publisher.events) == 1


@pytest.mark.parametrize("status", ["pending", "rejected", "withdrawn"])
def test_only_accepted_applications_can_submit(
    seeded_db, session, storage, publisher, status: str
) -> None:
    application_id = _application(seeded_db, 5, status)

    with pytest.raises(AppError) as exc_info:
        _submit(session, storage, publisher, application_id, [_file(PDF, "a.pdf")])

    assert _code(exc_info) == (409, "APPLICATION_NOT_ACCEPTED")
    assert publisher.events == []


def test_someone_elses_application_does_not_exist(seeded_db, session, storage, publisher) -> None:
    application_id = _application(seeded_db, 5)

    with pytest.raises(AppError) as exc_info:
        _submit(session, storage, publisher, application_id, contributor_id=6)

    assert _code(exc_info) == (404, "APPLICATION_NOT_FOUND")


def test_a_missing_application_does_not_exist(session, storage, publisher) -> None:
    with pytest.raises(AppError) as exc_info:
        _submit(session, storage, publisher, 999_999)
    assert _code(exc_info) == (404, "APPLICATION_NOT_FOUND")


def test_work_is_submitted_once(seeded_db, session, storage, publisher) -> None:
    application_id = _application(seeded_db, 5)
    _submit(session, storage, publisher, application_id)

    with pytest.raises(AppError) as exc_info:
        _submit(session, storage, publisher, application_id)

    assert _code(exc_info) == (409, "WORK_ALREADY_SUBMITTED")
    assert _count_submissions(session) == 1


def test_a_cancelled_opportunity_takes_no_work(seeded_db, session, storage, publisher) -> None:
    application_id = _application(seeded_db, 5)
    with seeded_db.cursor() as cur:
        cur.execute("UPDATE opportunity SET status = 'cancelled' WHERE opportunity_id = 1")

    with pytest.raises(AppError) as exc_info:
        _submit(session, storage, publisher, application_id)

    assert _code(exc_info) == (409, "OPPORTUNITY_CANCELLED")


def test_a_closed_opportunity_still_takes_work(seeded_db, session, storage, publisher) -> None:
    application_id = _application(seeded_db, 5)
    with seeded_db.cursor() as cur:
        cur.execute("UPDATE opportunity SET status = 'closed' WHERE opportunity_id = 1")

    assert _submit(session, storage, publisher, application_id).application_id == application_id


def test_at_most_five_files(seeded_db, session, storage, publisher, tmp_path) -> None:
    files = [_file(PDF, f"{i}.pdf") for i in range(submission_rules.MAX_FILES + 1)]

    with pytest.raises(AppError) as exc_info:
        _submit(session, storage, publisher, _application(seeded_db, 5), files)

    assert _code(exc_info) == (422, "TOO_MANY_FILES")
    assert _stored_files(tmp_path) == []


@pytest.mark.parametrize(
    ("data", "expected"),
    [(EXE, (415, "UNSUPPORTED_FILE_TYPE")), (b"", (422, "EMPTY_FILE"))],
)
def test_a_bad_file_refuses_the_whole_submission(
    seeded_db, session, storage, publisher, tmp_path, data: bytes, expected: tuple[int, str]
) -> None:
    files = [_file(PDF, "fine.pdf"), _file(data, "report.pdf")]

    with pytest.raises(AppError) as exc_info:
        _submit(session, storage, publisher, _application(seeded_db, 5), files)

    assert _code(exc_info) == expected
    assert _stored_files(tmp_path) == []
    assert _count_submissions(session) == 0


def test_an_oversized_file_removes_the_files_already_written(
    seeded_db, session, storage, publisher, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(submission_rules, "MAX_FILE_BYTES", 200)
    files = [_file(PDF, "small.pdf"), _file(b"%PDF-" + b"x" * 300, "big.pdf")]

    with pytest.raises(AppError) as exc_info:
        _submit(session, storage, publisher, _application(seeded_db, 5), files)

    assert _code(exc_info) == (413, "ATTACHMENT_TOO_LARGE")
    assert _stored_files(tmp_path) == []
    assert _count_submissions(session) == 0
    assert publisher.events == []


def test_a_race_on_the_unique_key_still_reports_already_submitted(
    seeded_db, session, storage, publisher, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    application_id = _application(seeded_db, 5)
    _submit(session, storage, publisher, application_id)
    before = _stored_files(tmp_path)
    # As if the check ran before a concurrent submission committed.
    monkeypatch.setattr(
        submission_service.application_repository, "has_submission", lambda s, a: False
    )

    with pytest.raises(AppError) as exc_info:
        _submit(session, storage, publisher, application_id, [_file(PDF, "late.pdf")])

    assert _code(exc_info) == (409, "WORK_ALREADY_SUBMITTED")
    assert _stored_files(tmp_path) == before


def test_the_trigger_backstop_reports_not_accepted(
    seeded_db, session, storage, publisher, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    application_id = _application(seeded_db, 5, "pending")
    monkeypatch.setattr(submission_service, "_check_can_submit", lambda s, a: None)

    with pytest.raises(AppError) as exc_info:
        _submit(session, storage, publisher, application_id, [_file(PDF, "a.pdf")])

    assert _code(exc_info) == (409, "APPLICATION_NOT_ACCEPTED")
    assert _stored_files(tmp_path) == []


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


@pytest.fixture
def submitted(seeded_db, session, storage, publisher):
    application_id = _application(seeded_db, 5)
    return _submit(session, storage, publisher, application_id, [_file(PDF, "sheets.pdf")])


@pytest.mark.parametrize("user_id", [5, 2])  # the applicant and the owning creator
def test_the_applicant_and_the_owner_see_the_submission(session, submitted, user_id) -> None:
    seen = submission_service.get_for_application(
        session, _user(session, user_id), submitted.application_id
    )
    assert seen == submitted


@pytest.mark.parametrize("user_id", [3, 6])  # another creator, another contributor
def test_nobody_else_sees_the_submission(session, submitted, user_id) -> None:
    with pytest.raises(AppError) as exc_info:
        submission_service.get_for_application(
            session, _user(session, user_id), submitted.application_id
        )
    assert _code(exc_info) == (404, "APPLICATION_NOT_FOUND")


def test_no_submission_yet(seeded_db, session) -> None:
    application_id = _application(seeded_db, 5)
    with pytest.raises(AppError) as exc_info:
        submission_service.get_for_application(session, _user(session, 2), application_id)
    assert _code(exc_info) == (404, "SUBMISSION_NOT_FOUND")


def test_the_owner_downloads_an_attachment(session, storage, submitted) -> None:
    [attachment] = submitted.attachments

    download = submission_service.open_attachment(
        session, storage, _user(session, 2), submitted.submission_id, attachment.attachment_id
    )

    with download.stream as stream:
        assert stream.read() == PDF
    assert (download.file_name, download.content_type, download.size_bytes) == (
        "sheets.pdf",
        "application/pdf",
        len(PDF),
    )


@pytest.mark.parametrize(
    ("user_id", "submission_offset", "attachment_offset"),
    [
        (3, 0, 0),  # another creator
        (6, 0, 0),  # another contributor
        (2, 0, 1),  # an attachment id that doesn't exist
        (2, 1, 0),  # a submission id that doesn't exist
    ],
)
def test_attachments_nobody_may_see_are_not_found(
    session, storage, submitted, user_id, submission_offset, attachment_offset
) -> None:
    [attachment] = submitted.attachments
    with pytest.raises(AppError) as exc_info:
        submission_service.open_attachment(
            session,
            storage,
            _user(session, user_id),
            submitted.submission_id + submission_offset,
            attachment.attachment_id + attachment_offset,
        )
    assert _code(exc_info) == (404, "ATTACHMENT_NOT_FOUND")


def test_a_missing_file_is_not_found(session, storage, submitted, tmp_path) -> None:
    for path in _stored_files(tmp_path):
        path.unlink()
    [attachment] = submitted.attachments

    with pytest.raises(AppError) as exc_info:
        submission_service.open_attachment(
            session, storage, _user(session, 2), submitted.submission_id, attachment.attachment_id
        )
    assert _code(exc_info) == (404, "ATTACHMENT_NOT_FOUND")


def test_a_key_the_store_cannot_hold_is_not_found(seeded_db, session, storage, submitted) -> None:
    """Like the dev seed's placeholder keys (004_seed_workflow.sql): a 404, not a 500."""
    [attachment] = submitted.attachments
    with seeded_db.cursor() as cur:
        cur.execute(
            "UPDATE submission_attachment SET storage_key = %s WHERE attachment_id = %s",
            ("dev/submissions/3/count-sheets.pdf", attachment.attachment_id),
        )
    session.rollback()

    with pytest.raises(AppError) as exc_info:
        submission_service.open_attachment(
            session, storage, _user(session, 2), submitted.submission_id, attachment.attachment_id
        )
    assert _code(exc_info) == (404, "ATTACHMENT_NOT_FOUND")
