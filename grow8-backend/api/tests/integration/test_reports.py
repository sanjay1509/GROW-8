"""Opportunity reports and admin takedown over HTTP (ADR 0016): status codes, response
bodies, role guards, events and what the creator can (not) see. The rules themselves
are covered in depth by test_report_service.py.

Opportunity 1 belongs to Maple Street Bakery (`bakery`, Priya Nair). `contributor` is
Alex Chen, `jordan` another contributor, `events_org` another creator and `admin` Ada
Admin. "Now" is frozen at 2026-10-16 12:00 UTC.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from grow8_common.events import EventType

from tests.conftest import _login
from tests.fakes import FakePublisher

REPORT = {"reason": "misleading_terms", "details": "Says paid, but the details say unpaid."}


@pytest.fixture
def admin(client: TestClient) -> dict[str, str]:
    return _login(client, "admin@grow8.dev")


def _error(response: Any, status: int) -> str:
    assert response.status_code == status, response.text
    return response.json()["error"]["code"]


def _ok(response: Any, status: int = 200) -> Any:
    assert response.status_code == status, response.text
    return response.json()


def _report(client: TestClient, headers: dict[str, str], opportunity_id: int = 1, **body) -> Any:
    return client.post(
        f"/api/v1/opportunities/{opportunity_id}/reports", json=body or REPORT, headers=headers
    )


def _review(client: TestClient, admin: dict[str, str], report_id: int, **body) -> Any:
    return client.post(f"/api/v1/admin/reports/{report_id}/review", json=body, headers=admin)


# ---------------------------------------------------------------------------
# The whole flow
# ---------------------------------------------------------------------------


def test_report_then_take_down(
    client: TestClient,
    contributor: dict[str, str],
    jordan: dict[str, str],
    bakery: dict[str, str],
    admin: dict[str, str],
    publisher: FakePublisher,
) -> None:
    alex = _ok(_report(client, contributor), 201)
    assert alex["opportunity"] == {
        "opportunity_id": 1,
        "title": "Digitize paper recipe archive",
        "status": "open",
    }
    assert (alex["reason"], alex["status"], alex["review"]) == ("misleading_terms", "pending", None)
    assert alex["created_at"] == "2026-10-16T12:00:00Z"
    assert "reporter" not in alex
    assert publisher.events[-1].event_type == EventType.OPPORTUNITY_REPORTED
    jordan_report = _ok(_report(client, jordan, reason="scam_or_spam"), 201)

    queue = _ok(client.get("/api/v1/admin/reports?status=pending", headers=admin))
    assert [(r["report_id"], r["open_reports_on_opportunity"]) for r in queue["items"]] == [
        (alex["report_id"], 2),
        (jordan_report["report_id"], 2),
    ]
    assert queue["items"][0]["reporter"] == {"user_id": 5, "full_name": "Alex Chen"}

    reviewed = _ok(
        _review(client, admin, alex["report_id"], decision="upheld", reason="Pay is misstated.")
    )
    assert reviewed["status"] == "upheld"
    assert reviewed["opportunity"]["status"] == "cancelled"
    assert reviewed["review"]["reason"] == "Pay is misstated."
    assert reviewed["open_reports_on_opportunity"] == 0
    assert publisher.events[-1].event_type == EventType.OPPORTUNITY_TAKEN_DOWN

    # The creator sees a cancelled opportunity, and nothing about who reported it.
    opportunity = _ok(client.get("/api/v1/opportunities/1", headers=bakery))
    assert opportunity["status"] == "cancelled"
    assert "Alex" not in str(opportunity) and "report" not in str(opportunity).lower()

    # Both reporters see the outcome; the browse list no longer shows it.
    mine = _ok(client.get("/api/v1/reports/mine", headers=jordan))["items"]
    assert [(r["report_id"], r["status"]) for r in mine] == [(jordan_report["report_id"], "upheld")]
    listed = _ok(client.get("/api/v1/opportunities?limit=100"))["items"]
    assert 1 not in [o["opportunity_id"] for o in listed]


def test_dismiss(
    client: TestClient, contributor: dict[str, str], admin: dict[str, str], publisher: FakePublisher
) -> None:
    report = _ok(_report(client, contributor), 201)

    reviewed = _ok(_review(client, admin, report["report_id"], decision="dismissed"))

    assert (reviewed["status"], reviewed["review"]["reason"]) == ("dismissed", None)
    assert reviewed["opportunity"]["status"] == "open"
    assert publisher.events[-1].event_type == EventType.REPORT_DISMISSED


# ---------------------------------------------------------------------------
# Reporting: refusals
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("who", ["bakery", "events_org", "admin"])
def test_only_contributors_report(
    client: TestClient, who: str, request: pytest.FixtureRequest
) -> None:
    response = _report(client, request.getfixturevalue(who))
    assert _error(response, 403) == "ROLE_FORBIDDEN"


def test_reporting_needs_a_token(client: TestClient) -> None:
    assert _error(_report(client, {}), 401) == "AUTH_REQUIRED"


def test_reported_once(client: TestClient, contributor: dict[str, str]) -> None:
    _ok(_report(client, contributor), 201)
    again = _report(client, contributor, reason="other")
    assert _error(again, 409) == "OPPORTUNITY_ALREADY_REPORTED"


@pytest.mark.parametrize("opportunity_id", [15, 999999])
def test_drafts_and_missing_opportunities(
    client: TestClient, contributor: dict[str, str], opportunity_id: int
) -> None:
    response = _report(client, contributor, opportunity_id)
    assert _error(response, 404) == "OPPORTUNITY_NOT_FOUND"


@pytest.mark.parametrize(
    "body",
    [
        {"reason": "boring"},
        {"details": "No reason given."},
        {"reason": "other", "details": "x" * 2_001},
        {"reason": "other", "anonymous": False},
    ],
)
def test_malformed_reports(client: TestClient, contributor: dict[str, str], body: dict) -> None:
    response = client.post("/api/v1/opportunities/1/reports", json=body, headers=contributor)
    assert _error(response, 422) == "VALIDATION_ERROR"


def test_my_reports_are_for_contributors(client: TestClient, bakery: dict[str, str]) -> None:
    assert _error(client.get("/api/v1/reports/mine", headers=bakery), 403) == "ROLE_FORBIDDEN"


# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("who", ["contributor", "bakery"])
def test_admin_report_routes_are_for_admins(
    client: TestClient, contributor: dict[str, str], who: str, request: pytest.FixtureRequest
) -> None:
    report = _ok(_report(client, contributor), 201)
    headers = request.getfixturevalue(who)

    assert _error(client.get("/api/v1/admin/reports", headers=headers), 403) == "ROLE_FORBIDDEN"
    response = _review(client, headers, report["report_id"], decision="dismissed")
    assert _error(response, 403) == "ROLE_FORBIDDEN"


def test_a_takedown_needs_a_reason(
    client: TestClient, contributor: dict[str, str], admin: dict[str, str]
) -> None:
    report = _ok(_report(client, contributor), 201)
    response = _review(client, admin, report["report_id"], decision="upheld", reason=" ")
    assert _error(response, 422) == "TAKEDOWN_REASON_REQUIRED"


def test_reviewed_once(
    client: TestClient, contributor: dict[str, str], admin: dict[str, str]
) -> None:
    report = _ok(_report(client, contributor), 201)
    _ok(_review(client, admin, report["report_id"], decision="dismissed"))

    again = _review(client, admin, report["report_id"], decision="upheld", reason="Changed mind")
    assert _error(again, 409) == "REPORT_ALREADY_REVIEWED"


def test_reviewing_a_missing_report(client: TestClient, admin: dict[str, str]) -> None:
    response = _review(client, admin, 999_999, decision="dismissed")
    assert _error(response, 404) == "REPORT_NOT_FOUND"


@pytest.mark.parametrize(
    "body",
    [
        {"decision": "approved"},
        {"decision": "dismissed", "reason": "x" * 501},
        {"decision": "dismissed", "notify_creator": True},
    ],
)
def test_malformed_reviews(
    client: TestClient, contributor: dict[str, str], admin: dict[str, str], body: dict
) -> None:
    report = _ok(_report(client, contributor), 201)
    assert _error(_review(client, admin, report["report_id"], **body), 422) == "VALIDATION_ERROR"


@pytest.mark.parametrize("query", ["status=open", "opportunity_id=0", "limit=101"])
def test_malformed_queue_filters(client: TestClient, admin: dict[str, str], query: str) -> None:
    response = client.get(f"/api/v1/admin/reports?{query}", headers=admin)
    assert _error(response, 422) == "VALIDATION_ERROR"
