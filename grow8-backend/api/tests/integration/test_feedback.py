"""Feedback, admin review and ratings over HTTP (ADR 0015): status codes, response
bodies, role guards and events. The rules themselves are covered in depth by
test_feedback_service.py.

Each test runs the whole flow through the API: Alex Chen (`contributor`) applies to
opportunity 1 of Maple Street Bakery (`bakery`, Priya Nair, user 2), is accepted,
submits 6.5 hours of work, and Priya verifies it. `events_org` owns another
organization, `jordan` is another contributor and `admin` is Ada Admin. "Now" is
frozen at 2026-10-16 12:00 UTC.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from grow8_common.events import EventType

from tests.conftest import _login
from tests.fakes import FakePublisher


@pytest.fixture
def admin(client: TestClient) -> dict[str, str]:
    return _login(client, "admin@grow8.dev")


def _error(response: Any, status: int) -> str:
    assert response.status_code == status, response.text
    return response.json()["error"]["code"]


def _ok(response: Any, status: int = 200) -> Any:
    assert response.status_code == status, response.text
    return response.json()


def _accepted_with_work(
    client: TestClient, contributor: dict[str, str], creator: dict[str, str]
) -> tuple[int, int]:
    application = _ok(
        client.post("/api/v1/opportunities/1/applications", json={}, headers=contributor), 201
    )["application_id"]
    _ok(
        client.post(
            f"/api/v1/applications/{application}/decision",
            json={"decision": "accepted"},
            headers=creator,
        )
    )
    submission = _ok(
        client.post(
            f"/api/v1/applications/{application}/submission",
            data={"description": "Typed up 40 recipes.", "hours_claimed": "6.5"},
            headers=contributor,
        ),
        201,
    )["submission_id"]
    return application, submission


def _verify(client: TestClient, creator: dict[str, str], submission_id: int) -> None:
    _ok(
        client.post(
            f"/api/v1/submissions/{submission_id}/verification",
            json={"decision": "approved", "verified_hours": "6"},
            headers=creator,
        )
    )


@pytest.fixture
def unverified(client: TestClient, contributor: dict[str, str], bakery: dict[str, str]) -> tuple:
    return _accepted_with_work(client, contributor, bakery)


@pytest.fixture
def application_id(client: TestClient, bakery: dict[str, str], unverified: tuple) -> int:
    application, submission = unverified
    _verify(client, bakery, submission)
    return application


def _give(client: TestClient, headers: dict[str, str], application_id: int, **body) -> Any:
    body.setdefault("rating", 5)
    return client.post(
        f"/api/v1/applications/{application_id}/feedback", json=body, headers=headers
    )


def _seen(client: TestClient, headers: dict[str, str], application_id: int) -> Any:
    return _ok(client.get(f"/api/v1/applications/{application_id}/feedback", headers=headers))


def _review(client: TestClient, admin: dict[str, str], feedback_id: int, **body) -> Any:
    return client.post(f"/api/v1/admin/feedback/{feedback_id}/review", json=body, headers=admin)


def _rating(client: TestClient, user_id: int) -> tuple[str | None, int]:
    body = _ok(client.get(f"/api/v1/users/{user_id}/rating"))  # public: no token
    return body["average_rating"], body["approved_feedback_count"]


# ---------------------------------------------------------------------------
# The whole flow
# ---------------------------------------------------------------------------


def test_feedback_is_moderated_before_it_counts(
    client: TestClient,
    contributor: dict[str, str],
    bakery: dict[str, str],
    admin: dict[str, str],
    application_id: int,
    publisher: FakePublisher,
) -> None:
    given = _ok(
        _give(client, contributor, application_id, rating=4, comment="  Clear and kind.  "), 201
    )
    assert given["author"] == {"user_id": 5, "full_name": "Alex Chen"}
    assert given["subject"] == {"user_id": 2, "full_name": "Priya Nair"}
    assert (given["rating"], given["comment"], given["status"], given["review"]) == (
        4,
        "Clear and kind.",
        "pending",
        None,
    )
    assert given["reports_discrepancy"] is False
    assert given["created_at"] == "2026-10-16T12:00:00Z"
    assert publisher.events[-1].event_type == EventType.FEEDBACK_SUBMITTED

    # Pending: the author sees it, the subject doesn't, and the rating doesn't move.
    assert _seen(client, contributor, application_id)["given"]["status"] == "pending"
    assert _seen(client, bakery, application_id) == {"given": None, "received": None}
    assert _rating(client, 2) == (None, 0)

    queue = _ok(client.get("/api/v1/admin/feedback?status=pending", headers=admin))
    assert [f["feedback_id"] for f in queue["items"]] == [given["feedback_id"]]

    reviewed = _ok(_review(client, admin, given["feedback_id"], decision="approved"))
    assert reviewed["status"] == "approved"
    assert reviewed["review"]["decision"] == "approved"
    assert publisher.events[-1].event_type == EventType.FEEDBACK_APPROVED

    # Approved: the subject sees it and it counts.
    assert _seen(client, bakery, application_id)["received"]["feedback_id"] == given["feedback_id"]
    assert _rating(client, 2) == ("4.00", 1)


def test_rejected_feedback_never_counts_or_reaches_the_subject(
    client: TestClient,
    contributor: dict[str, str],
    bakery: dict[str, str],
    admin: dict[str, str],
    application_id: int,
    publisher: FakePublisher,
) -> None:
    given = _ok(_give(client, bakery, application_id, rating=1, reports_discrepancy=True), 201)

    reviewed = _ok(
        _review(client, admin, given["feedback_id"], decision="rejected", reason="Not specific.")
    )

    assert reviewed["review"]["reason"] == "Not specific."
    assert publisher.events[-1].event_type == EventType.FEEDBACK_REJECTED
    assert _seen(client, bakery, application_id)["given"]["status"] == "rejected"
    assert _seen(client, contributor, application_id) == {"given": None, "received": None}
    assert _rating(client, 5) == (None, 0)


# ---------------------------------------------------------------------------
# Giving feedback: refusals
# ---------------------------------------------------------------------------


def test_feedback_waits_for_verified_work(
    client: TestClient, contributor: dict[str, str], unverified: tuple
) -> None:
    application, _ = unverified
    assert _error(_give(client, contributor, application), 409) == "WORK_NOT_VERIFIED"


def test_one_feedback_per_author(
    client: TestClient, contributor: dict[str, str], application_id: int
) -> None:
    _ok(_give(client, contributor, application_id), 201)
    again = _give(client, contributor, application_id, rating=1)
    assert _error(again, 409) == "FEEDBACK_ALREADY_SUBMITTED"


@pytest.mark.parametrize("who", ["events_org", "jordan", "admin"])
def test_non_participants_get_404(
    client: TestClient, application_id: int, who: str, request: pytest.FixtureRequest
) -> None:
    headers = request.getfixturevalue(who)
    assert _error(_give(client, headers, application_id), 404) == "APPLICATION_NOT_FOUND"
    response = client.get(f"/api/v1/applications/{application_id}/feedback", headers=headers)
    assert _error(response, 404) == "APPLICATION_NOT_FOUND"


def test_feedback_needs_a_token(client: TestClient, application_id: int) -> None:
    assert _error(_give(client, {}, application_id), 401) == "AUTH_REQUIRED"


@pytest.mark.parametrize(
    "body",
    [
        {"rating": 0},
        {"rating": 6},
        {"rating": 4.5},
        {"rating": None},
        {"rating": 3, "comment": "x" * 2_001},
        {"rating": 3, "subject_user_id": 3},  # the subject is never chosen by the client
    ],
)
def test_malformed_feedback(
    client: TestClient, contributor: dict[str, str], application_id: int, body: dict
) -> None:
    response = client.post(
        f"/api/v1/applications/{application_id}/feedback", json=body, headers=contributor
    )
    assert _error(response, 422) == "VALIDATION_ERROR"


# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("who", ["contributor", "bakery"])
def test_admin_routes_are_for_admins(
    client: TestClient, application_id: int, who: str, request: pytest.FixtureRequest
) -> None:
    headers = request.getfixturevalue(who)
    given = _ok(_give(client, headers, application_id), 201)

    assert _error(client.get("/api/v1/admin/feedback", headers=headers), 403) == "ROLE_FORBIDDEN"
    response = _review(client, headers, given["feedback_id"], decision="approved")
    assert _error(response, 403) == "ROLE_FORBIDDEN"


def test_admin_routes_need_a_token(client: TestClient) -> None:
    assert _error(client.get("/api/v1/admin/feedback"), 401) == "AUTH_REQUIRED"


def test_rejecting_needs_a_reason(
    client: TestClient, contributor: dict[str, str], admin: dict[str, str], application_id: int
) -> None:
    given = _ok(_give(client, contributor, application_id), 201)
    response = _review(client, admin, given["feedback_id"], decision="rejected", reason="  ")
    assert _error(response, 422) == "REJECTION_REASON_REQUIRED"


def test_reviewed_once(
    client: TestClient, contributor: dict[str, str], admin: dict[str, str], application_id: int
) -> None:
    given = _ok(_give(client, contributor, application_id), 201)
    _ok(_review(client, admin, given["feedback_id"], decision="approved"))

    again = _review(client, admin, given["feedback_id"], decision="rejected", reason="Oops")
    assert _error(again, 409) == "FEEDBACK_ALREADY_REVIEWED"


def test_reviewing_missing_feedback(client: TestClient, admin: dict[str, str]) -> None:
    response = _review(client, admin, 999_999, decision="approved")
    assert _error(response, 404) == "FEEDBACK_NOT_FOUND"


@pytest.mark.parametrize(
    "body",
    [
        {"decision": "maybe"},
        {"decision": "rejected", "reason": "x" * 501},
        {"decision": "approved", "rating": 1},
    ],
)
def test_malformed_reviews(
    client: TestClient,
    contributor: dict[str, str],
    admin: dict[str, str],
    application_id: int,
    body: dict,
) -> None:
    given = _ok(_give(client, contributor, application_id), 201)
    assert _error(_review(client, admin, given["feedback_id"], **body), 422) == "VALIDATION_ERROR"


@pytest.mark.parametrize("query", ["status=open", "discrepancy=maybe", "limit=0"])
def test_malformed_queue_filters(client: TestClient, admin: dict[str, str], query: str) -> None:
    response = client.get(f"/api/v1/admin/feedback?{query}", headers=admin)
    assert _error(response, 422) == "VALIDATION_ERROR"


def test_queue_filters_by_discrepancy(
    client: TestClient,
    contributor: dict[str, str],
    bakery: dict[str, str],
    admin: dict[str, str],
    application_id: int,
) -> None:
    plain = _ok(_give(client, contributor, application_id), 201)["feedback_id"]
    flagged = _ok(_give(client, bakery, application_id, reports_discrepancy=True), 201)[
        "feedback_id"
    ]

    def ids(query: str) -> list[int]:
        response = client.get(f"/api/v1/admin/feedback{query}", headers=admin)
        return [f["feedback_id"] for f in _ok(response)["items"]]

    assert ids("") == [flagged, plain]  # discrepancy reports first
    assert ids("?discrepancy=true") == [flagged]
    assert ids("?discrepancy=false&status=pending") == [plain]


# ---------------------------------------------------------------------------
# Ratings
# ---------------------------------------------------------------------------


def test_a_user_with_no_feedback(client: TestClient) -> None:
    assert _ok(client.get("/api/v1/users/2/rating")) == {
        "user_id": 2,
        "average_rating": None,
        "approved_feedback_count": 0,
    }


def test_rating_of_an_unknown_user(client: TestClient) -> None:
    assert _error(client.get("/api/v1/users/999999/rating"), 404) == "USER_NOT_FOUND"
