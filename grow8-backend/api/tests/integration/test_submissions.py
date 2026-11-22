"""Work submission over HTTP (ADR 0012): multipart parsing, status codes, response
bodies, download headers and the event. The rules themselves are covered in depth by
test_submission_service.py; this checks the endpoints end to end.

Each test applies through the API as Alex Chen (`contributor`) to opportunity 1 of
Maple Street Bakery (`bakery`), which accepts. `events_org` owns another organization
and `jordan` is another contributor. "Now" is frozen at 2026-10-16 12:00 UTC.
"""

import io
import zipfile
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from grow8_common.events import EventType, WorkSubmittedPayload

from tests.fakes import FakePublisher

PDF = b"%PDF-1.7\n% GROW8 count sheets\n" + b"0" * 1_000
CSV = b"date,hours\n2026-10-15,3.5\n2026-10-16,3\n"
FORM = {"description": "Typed up 40 recipes into the shared sheet.", "hours_claimed": "6.5"}


def _xlsx() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("xl/workbook.xml", "<workbook/>")
    return buffer.getvalue()


def _error(response: Any, status: int) -> str:
    assert response.status_code == status, response.text
    return response.json()["error"]["code"]


def _stored_files(storage_dir: Path) -> list[Path]:
    return sorted(p for p in storage_dir.rglob("*") if p.is_file())


def _apply(client: TestClient, contributor: dict[str, str]) -> int:
    response = client.post("/api/v1/opportunities/1/applications", json={}, headers=contributor)
    assert response.status_code == 201, response.text
    return response.json()["application_id"]


def _decide(client: TestClient, creator: dict[str, str], application_id: int) -> None:
    response = client.post(
        f"/api/v1/applications/{application_id}/decision",
        json={"decision": "accepted"},
        headers=creator,
    )
    assert response.status_code == 200, response.text


@pytest.fixture
def accepted(client: TestClient, contributor: dict[str, str], bakery: dict[str, str]) -> int:
    application_id = _apply(client, contributor)
    _decide(client, bakery, application_id)
    return application_id


def _path(application_id: int) -> str:
    return f"/api/v1/applications/{application_id}/submission"


def _submit(
    client: TestClient,
    headers: dict[str, str],
    application_id: int,
    files: list[tuple[str, bytes, str]] = (),
    data: dict[str, str] = FORM,
) -> Any:
    return client.post(
        _path(application_id),
        data=data,
        files=[("files", f) for f in files] or None,
        headers=headers,
    )


# ---------------------------------------------------------------------------
# Submitting
# ---------------------------------------------------------------------------


def test_submit_with_files_then_read_and_download(
    client: TestClient,
    contributor: dict[str, str],
    bakery: dict[str, str],
    accepted: int,
    publisher: FakePublisher,
    storage_dir: Path,
) -> None:
    response = _submit(
        client,
        contributor,
        accepted,
        [
            ("count sheets.pdf", PDF, "application/pdf"),
            ("hours", _xlsx(), "application/octet-stream"),  # type comes from the content
            ("hours.csv", CSV, "text/csv"),
        ],
    )

    assert response.status_code == 201, response.text
    body = response.json()
    attachments = body.pop("attachments")
    submission_id = body.pop("submission_id")
    assert body == {
        "application_id": accepted,
        "status": "awaiting",
        "description": "Typed up 40 recipes into the shared sheet.",
        "hours_claimed": "6.50",
        "submitted_at": "2026-10-16T12:00:00Z",
        "opportunity": {
            "opportunity_id": 1,
            "title": "Digitize paper recipe archive",
            "status": "open",
        },
        "applicant": {"user_id": 5, "full_name": "Alex Chen"},
        "verification": None,
    }
    assert [(a["file_name"], a["content_type"], a["size_bytes"]) for a in attachments] == [
        ("count sheets.pdf", "application/pdf", len(PDF)),
        (
            "hours.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            len(_xlsx()),
        ),
        ("hours.csv", "text/csv", len(CSV)),
    ]
    assert len(_stored_files(storage_dir)) == 3

    # The applicant and the owning creator read the same thing back.
    for who in (contributor, bakery):
        again = client.get(_path(accepted), headers=who)
        assert again.status_code == 200
        assert again.json() == response.json()

    download = client.get(
        f"/api/v1/submissions/{submission_id}/attachments/{attachments[0]['attachment_id']}",
        headers=bakery,
    )
    assert download.status_code == 200
    assert download.content == PDF
    assert download.headers["content-type"] == "application/pdf"
    assert download.headers["content-disposition"].startswith(
        'attachment; filename="count sheets.pdf"'
    )
    assert download.headers["x-content-type-options"] == "nosniff"
    assert download.headers["cache-control"] == "private, no-store"

    [event] = [e for e in publisher.events if e.event_type == EventType.WORK_SUBMITTED]
    payload = WorkSubmittedPayload.model_validate(event.payload)
    assert (payload.submission_id, payload.application_id) == (submission_id, accepted)
    assert (payload.organization_id, payload.contributor_name) == (1, "Alex Chen")
    assert (payload.hours_claimed, payload.attachment_count) == (Decimal("6.5"), 3)
    assert event.correlation_id == response.headers["x-request-id"]


def test_files_are_optional(client: TestClient, contributor: dict[str, str], accepted: int) -> None:
    response = _submit(client, contributor, accepted)

    assert response.status_code == 201, response.text
    assert response.json()["attachments"] == []


@pytest.mark.parametrize(
    ("data", "field"),
    [
        ({"hours_claimed": "6.5"}, "description"),
        ({"description": "   ", "hours_claimed": "6.5"}, "description"),
        ({"description": "x" * 5_001, "hours_claimed": "6.5"}, "description"),
        ({"description": "Done"}, "hours_claimed"),
        ({"description": "Done", "hours_claimed": "six"}, "hours_claimed"),
        ({"description": "Done", "hours_claimed": "0"}, "hours_claimed"),
        ({"description": "Done", "hours_claimed": "1.255"}, "hours_claimed"),
        ({"description": "Done", "hours_claimed": "10000"}, "hours_claimed"),
    ],
)
def test_bad_form_fields_are_validation_errors(
    client: TestClient,
    contributor: dict[str, str],
    accepted: int,
    data: dict[str, str],
    field: str,
) -> None:
    response = _submit(client, contributor, accepted, data=data)

    assert _error(response, 422) == "VALIDATION_ERROR"
    assert ["body", field] in [d["loc"] for d in response.json()["error"]["details"]]


def test_signing_in_is_required(client: TestClient, accepted: int) -> None:
    assert _error(_submit(client, {}, accepted), 401) == "AUTH_REQUIRED"


def test_creators_cannot_submit_work(
    client: TestClient, bakery: dict[str, str], accepted: int
) -> None:
    assert _error(_submit(client, bakery, accepted), 403) == "ROLE_FORBIDDEN"


def test_someone_elses_application_is_not_found(
    client: TestClient, jordan: dict[str, str], accepted: int
) -> None:
    assert _error(_submit(client, jordan, accepted), 404) == "APPLICATION_NOT_FOUND"


def test_a_pending_application_cannot_submit(
    client: TestClient, contributor: dict[str, str]
) -> None:
    application_id = _apply(client, contributor)

    response = _submit(client, contributor, application_id)

    assert _error(response, 409) == "APPLICATION_NOT_ACCEPTED"


def test_work_is_submitted_once(
    client: TestClient, contributor: dict[str, str], accepted: int
) -> None:
    assert _submit(client, contributor, accepted).status_code == 201

    assert _error(_submit(client, contributor, accepted), 409) == "WORK_ALREADY_SUBMITTED"


def test_after_submitting_the_application_cannot_be_withdrawn_nor_the_opportunity_cancelled(
    client: TestClient, contributor: dict[str, str], bakery: dict[str, str], accepted: int
) -> None:
    assert _submit(client, contributor, accepted).status_code == 201

    withdraw = client.post(f"/api/v1/applications/{accepted}/withdraw", headers=contributor)
    cancel = client.post("/api/v1/opportunities/1/cancel", headers=bakery)

    assert _error(withdraw, 409) == "WORK_ALREADY_SUBMITTED"
    assert _error(cancel, 409) == "WORK_ALREADY_SUBMITTED"


def test_a_cancelled_opportunity_takes_no_work(
    client: TestClient, contributor: dict[str, str], bakery: dict[str, str], accepted: int
) -> None:
    assert client.post("/api/v1/opportunities/1/cancel", headers=bakery).status_code == 200

    assert _error(_submit(client, contributor, accepted), 409) == "OPPORTUNITY_CANCELLED"


def test_more_than_five_files_is_refused(
    client: TestClient, contributor: dict[str, str], accepted: int, storage_dir: Path
) -> None:
    files = [(f"{i}.pdf", PDF, "application/pdf") for i in range(6)]

    assert _error(_submit(client, contributor, accepted, files), 422) == "TOO_MANY_FILES"
    assert _stored_files(storage_dir) == []


@pytest.mark.parametrize(
    ("content", "status", "code"),
    [
        (b"MZ\x90\x00\x03\x00\x00\x00", 415, "UNSUPPORTED_FILE_TYPE"),  # a Windows .exe
        (b"", 422, "EMPTY_FILE"),
    ],
)
def test_a_bad_file_refuses_the_submission(
    client: TestClient,
    contributor: dict[str, str],
    accepted: int,
    storage_dir: Path,
    content: bytes,
    status: int,
    code: str,
) -> None:
    files = [("fine.pdf", PDF, "application/pdf"), ("report.pdf", content, "application/pdf")]

    assert _error(_submit(client, contributor, accepted, files), status) == code
    assert _stored_files(storage_dir) == []
    assert _error(client.get(_path(accepted), headers=contributor), 404) == "SUBMISSION_NOT_FOUND"


def test_a_file_over_5_mb_is_refused(
    client: TestClient, contributor: dict[str, str], accepted: int, storage_dir: Path
) -> None:
    big = b"%PDF-" + b"0" * (5 * 1024 * 1024)

    response = _submit(client, contributor, accepted, [("big.pdf", big, "application/pdf")])

    assert _error(response, 413) == "ATTACHMENT_TOO_LARGE"
    assert _stored_files(storage_dir) == []


def test_an_oversized_request_is_refused_before_it_is_read(
    client: TestClient, contributor: dict[str, str], accepted: int
) -> None:
    huge = b"%PDF-" + b"0" * (26 * 1024 * 1024)

    response = _submit(client, contributor, accepted, [("huge.pdf", huge, "application/pdf")])

    assert _error(response, 413) == "ATTACHMENT_TOO_LARGE"
    assert (
        response.json()["error"]["message"] == "A submission can have at most 5 files of 5 MB each"
    )


def test_a_submission_without_content_length_is_refused(
    client: TestClient, contributor: dict[str, str], accepted: int
) -> None:
    def chunked():  # httpx sends an iterator body chunked, without Content-Length
        yield b"--x\r\n"

    response = client.post(
        _path(accepted),
        content=chunked(),
        headers={**contributor, "Content-Type": "multipart/form-data; boundary=x"},
    )

    assert _error(response, 411) == "LENGTH_REQUIRED"


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


def test_nothing_submitted_yet(client: TestClient, bakery: dict[str, str], accepted: int) -> None:
    assert _error(client.get(_path(accepted), headers=bakery), 404) == "SUBMISSION_NOT_FOUND"


def test_other_people_cannot_see_the_submission_or_its_files(
    client: TestClient,
    contributor: dict[str, str],
    events_org: dict[str, str],
    jordan: dict[str, str],
    accepted: int,
) -> None:
    body = _submit(client, contributor, accepted, [("sheets.pdf", PDF, "application/pdf")]).json()
    download = (
        f"/api/v1/submissions/{body['submission_id']}"
        f"/attachments/{body['attachments'][0]['attachment_id']}"
    )

    for who in (events_org, jordan):
        assert _error(client.get(_path(accepted), headers=who), 404) == "APPLICATION_NOT_FOUND"
        assert _error(client.get(download, headers=who), 404) == "ATTACHMENT_NOT_FOUND"


# ---------------------------------------------------------------------------
# What the frontend needs around it
# ---------------------------------------------------------------------------


def test_applications_say_whether_work_was_submitted(
    client: TestClient, contributor: dict[str, str], bakery: dict[str, str], accepted: int
) -> None:
    def submission_ids() -> list[Any]:
        return [
            client.get(f"/api/v1/applications/{accepted}", headers=contributor).json(),
            client.get("/api/v1/applications/mine", headers=contributor).json()["items"][0],
            client.get("/api/v1/applications/received", headers=bakery).json()["items"][0],
        ]

    assert [a["submission_id"] for a in submission_ids()] == [None, None, None]

    submission_id = _submit(client, contributor, accepted).json()["submission_id"]

    assert [a["submission_id"] for a in submission_ids()] == [submission_id] * 3


def test_a_browser_on_another_origin_can_read_the_download_file_name(
    client: TestClient, contributor: dict[str, str], bakery: dict[str, str], accepted: int
) -> None:
    body = _submit(client, contributor, accepted, [("sheets.pdf", PDF, "application/pdf")]).json()
    attachment_id = body["attachments"][0]["attachment_id"]

    download = client.get(
        f"/api/v1/submissions/{body['submission_id']}/attachments/{attachment_id}",
        headers={**bakery, "Origin": "http://localhost:5173"},
    )

    assert download.status_code == 200
    assert download.headers["access-control-allow-origin"] == "http://localhost:5173"
    exposed = download.headers["access-control-expose-headers"].lower().split(", ")
    assert "content-disposition" in exposed
