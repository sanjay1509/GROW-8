"""Work verification and the submission reads over HTTP (ADR 0013): status codes,
response bodies, the event, and `work_status` on applications. The rules themselves are
covered in depth by test_verification_service.py.

Each test applies through the API as Alex Chen (`contributor`) to opportunity 1 of
Maple Street Bakery (`bakery`), which accepts, and Alex submits 6.5 hours of work.
`events_org` owns another organization and `jordan` is another contributor. "Now" is
frozen at 2026-10-16 12:00 UTC.
"""

from decimal import Decimal
from typing import Any

import pymysql
import pytest
from fastapi.testclient import TestClient
from grow8_common.events import EventType, WorkRejectedPayload, WorkVerifiedPayload

from tests.fakes import FakePublisher


def _error(response: Any, status: int) -> str:
    assert response.status_code == status, response.text
    return response.json()["error"]["code"]


def _accepted(client: TestClient, contributor: dict[str, str], creator: dict[str, str]) -> int:
    response = client.post("/api/v1/opportunities/1/applications", json={}, headers=contributor)
    assert response.status_code == 201, response.text
    application_id = response.json()["application_id"]
    response = client.post(
        f"/api/v1/applications/{application_id}/decision",
        json={"decision": "accepted"},
        headers=creator,
    )
    assert response.status_code == 200, response.text
    return application_id


def _submit(client: TestClient, contributor: dict[str, str], application_id: int) -> int:
    response = client.post(
        f"/api/v1/applications/{application_id}/submission",
        data={"description": "Typed up 40 recipes.", "hours_claimed": "6.5"},
        headers=contributor,
    )
    assert response.status_code == 201, response.text
    return response.json()["submission_id"]


@pytest.fixture
def application_id(client: TestClient, contributor: dict[str, str], bakery: dict[str, str]) -> int:
    return _accepted(client, contributor, bakery)


@pytest.fixture
def submission_id(client: TestClient, contributor: dict[str, str], application_id: int) -> int:
    return _submit(client, contributor, application_id)


def _verify(client: TestClient, headers: dict[str, str], submission_id: int, **body) -> Any:
    return client.post(
        f"/api/v1/submissions/{submission_id}/verification", json=body, headers=headers
    )


def _work_status(client: TestClient, headers: dict[str, str], application_id: int) -> str:
    response = client.get(f"/api/v1/applications/{application_id}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()["work_status"]


# ---------------------------------------------------------------------------
# Verifying
# ---------------------------------------------------------------------------


def test_approve_then_both_parties_read_it(
    client: TestClient,
    contributor: dict[str, str],
    bakery: dict[str, str],
    application_id: int,
    submission_id: int,
    publisher: FakePublisher,
) -> None:
    response = _verify(client, bakery, submission_id, decision="approved", verified_hours="6")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "approved"
    assert body["verification"] == {
        "decision": "approved",
        "verified_hours": "6.00",
        "comment": None,
        "verified_at": "2026-10-16T12:00:00Z",
    }
    assert body["hours_claimed"] == "6.50"

    for who in (contributor, bakery):
        again = client.get(f"/api/v1/submissions/{submission_id}", headers=who)
        assert again.status_code == 200
        assert again.json() == body
        assert _work_status(client, who, application_id) == "completed"

    [event] = [e for e in publisher.events if e.event_type == EventType.WORK_VERIFIED]
    payload = WorkVerifiedPayload.model_validate(event.payload)
    assert (payload.submission_id, payload.contributor_id, payload.verified_hours) == (
        submission_id,
        5,
        Decimal("6.00"),
    )


def test_reject_with_a_comment(
    client: TestClient,
    contributor: dict[str, str],
    bakery: dict[str, str],
    application_id: int,
    submission_id: int,
    publisher: FakePublisher,
) -> None:
    response = _verify(
        client, bakery, submission_id, decision="rejected", comment="  Half is missing.  "
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "rejected"
    assert response.json()["verification"]["comment"] == "Half is missing."
    assert response.json()["verification"]["verified_hours"] is None
    assert _work_status(client, contributor, application_id) == "work_rejected"

    [event] = [e for e in publisher.events if e.event_type == EventType.WORK_REJECTED]
    assert WorkRejectedPayload.model_validate(event.payload).comment == "Half is missing."


def test_work_status_follows_the_application(
    client: TestClient, contributor: dict[str, str], bakery: dict[str, str], application_id: int
) -> None:
    assert _work_status(client, contributor, application_id) == "not_submitted"
    _submit(client, contributor, application_id)
    assert _work_status(client, contributor, application_id) == "awaiting_verification"

    listed = client.get("/api/v1/applications/mine", headers=contributor).json()["items"]
    assert [a["work_status"] for a in listed] == ["awaiting_verification"]
    received = client.get("/api/v1/applications/received", headers=bakery).json()["items"]
    assert [a["work_status"] for a in received] == ["awaiting_verification"]


def test_more_hours_than_claimed(client: TestClient, bakery: dict[str, str], submission_id) -> None:
    response = _verify(client, bakery, submission_id, decision="approved", verified_hours="6.51")
    assert _error(response, 422) == "VERIFIED_HOURS_EXCEED_CLAIMED"


@pytest.mark.parametrize("extra", [{}, {"comment": ""}, {"comment": "   "}])
def test_rejecting_needs_a_comment(
    client: TestClient, bakery: dict[str, str], submission_id: int, extra: dict
) -> None:
    response = _verify(client, bakery, submission_id, decision="rejected", **extra)
    assert _error(response, 422) == "REJECTION_COMMENT_REQUIRED"


@pytest.mark.parametrize(
    "body",
    [
        {"decision": "approved"},  # hours are required when approving
        {"decision": "approved", "verified_hours": "0"},
        {"decision": "approved", "verified_hours": "-1"},
        {"decision": "approved", "verified_hours": "1.234"},
        {"decision": "rejected", "verified_hours": "2", "comment": "No."},  # no hours here
        {"decision": "maybe", "verified_hours": "2"},
        {"decision": "rejected", "comment": "x" * 2_001},
        {"decision": "approved", "verified_hours": "2", "verified_by": 3},  # unknown field
    ],
)
def test_malformed_bodies_are_validation_errors(
    client: TestClient, bakery: dict[str, str], submission_id: int, body: dict
) -> None:
    response = _verify(client, bakery, submission_id, **body)
    assert _error(response, 422) == "VALIDATION_ERROR"


def test_verified_once(client: TestClient, bakery: dict[str, str], submission_id: int) -> None:
    _verify(client, bakery, submission_id, decision="approved", verified_hours="6")

    again = _verify(client, bakery, submission_id, decision="rejected", comment="Changed my mind")

    assert _error(again, 409) == "SUBMISSION_ALREADY_VERIFIED"


def test_another_creator_cannot_verify(
    client: TestClient,
    contributor: dict[str, str],
    events_org: dict[str, str],
    submission_id: int,
    publisher: FakePublisher,
) -> None:
    response = _verify(client, events_org, submission_id, decision="approved", verified_hours="6")

    assert _error(response, 404) == "SUBMISSION_NOT_FOUND"
    assert (
        client.get(f"/api/v1/submissions/{submission_id}", headers=contributor).json()[
            "verification"
        ]
        is None
    )
    assert not [e for e in publisher.events if e.event_type == EventType.WORK_VERIFIED]


def test_contributors_cannot_verify(
    client: TestClient, contributor: dict[str, str], submission_id: int
) -> None:
    response = _verify(client, contributor, submission_id, decision="approved", verified_hours="6")
    assert _error(response, 403) == "ROLE_FORBIDDEN"


def test_verifying_needs_a_token(client: TestClient, submission_id: int) -> None:
    response = _verify(client, {}, submission_id, decision="approved", verified_hours="6")
    assert _error(response, 401) == "AUTH_REQUIRED"


def test_a_cancelled_opportunity(
    client: TestClient, seeded_db: pymysql.Connection, bakery: dict[str, str], submission_id: int
) -> None:
    # Cancelling is refused once work is submitted (ADR 0011), so set it directly.
    with seeded_db.cursor() as cur:
        cur.execute("UPDATE opportunity SET status = 'cancelled' WHERE opportunity_id = 1")

    response = _verify(client, bakery, submission_id, decision="approved", verified_hours="6")

    assert _error(response, 409) == "OPPORTUNITY_CANCELLED"


def test_a_missing_submission(client: TestClient, bakery: dict[str, str]) -> None:
    response = _verify(client, bakery, 999_999, decision="approved", verified_hours="1")
    assert _error(response, 404) == "SUBMISSION_NOT_FOUND"


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("who", ["events_org", "jordan"])
def test_nobody_else_sees_a_submission(
    client: TestClient, submission_id: int, who: str, request: pytest.FixtureRequest
) -> None:
    response = client.get(
        f"/api/v1/submissions/{submission_id}", headers=request.getfixturevalue(who)
    )
    assert _error(response, 404) == "SUBMISSION_NOT_FOUND"


def test_review_queue(
    client: TestClient,
    bakery: dict[str, str],
    events_org: dict[str, str],
    jordan: dict[str, str],
    submission_id: int,
) -> None:
    second = _submit(client, jordan, _accepted(client, jordan, bakery))
    _verify(client, bakery, submission_id, decision="approved", verified_hours="6")

    def queue(headers: dict[str, str], query: str = "") -> list[tuple[int, str]]:
        response = client.get(f"/api/v1/submissions/received{query}", headers=headers)
        assert response.status_code == 200, response.text
        return [(s["submission_id"], s["status"]) for s in response.json()["items"]]

    assert queue(bakery) == [(submission_id, "approved"), (second, "awaiting")]
    assert queue(bakery, "?status=awaiting") == [(second, "awaiting")]
    assert queue(bakery, "?status=approved&status=rejected") == [(submission_id, "approved")]
    assert queue(bakery, "?opportunity_id=1&limit=1&offset=1") == [(second, "awaiting")]
    assert queue(events_org) == []

    item = client.get("/api/v1/submissions/received?status=awaiting", headers=bakery).json()
    assert item["total"] == 1
    assert item["items"][0]["applicant"] == {"user_id": 6, "full_name": "Jordan Lee"}
    assert item["items"][0]["opportunity"]["title"] == "Digitize paper recipe archive"


def test_review_queue_is_for_creators(client: TestClient, contributor: dict[str, str]) -> None:
    response = client.get("/api/v1/submissions/received", headers=contributor)
    assert _error(response, 403) == "ROLE_FORBIDDEN"


def test_review_queue_refuses_an_unknown_status(client: TestClient, bakery: dict[str, str]) -> None:
    response = client.get("/api/v1/submissions/received?status=pending", headers=bakery)
    assert _error(response, 422) == "VALIDATION_ERROR"
