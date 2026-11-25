"""What the owning creator learns about a takedown, and the creator shown to admins (#47).

Opportunity 1 is Maple Street Bakery's (Priya Nair, user 2). Reporters must stay
anonymous to the creator (ADR 0016 decision 2): no names, no own words, no count."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.conftest import DEV_PASSWORD

API = "/api/v1"
ALEX_WORDS = "I applied last week and they asked me to work unpaid."


def _login(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(f"{API}/auth/login", json={"email": email, "password": DEV_PASSWORD})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def admin(client: TestClient) -> dict[str, str]:
    return _login(client, "admin@grow8.dev")


def _error(response: Any, status: int) -> str:
    assert response.status_code == status, response.text
    return response.json()["error"]["code"]


def _report(client: TestClient, headers: dict[str, str], opportunity_id: int, **body: Any) -> int:
    response = client.post(
        f"{API}/opportunities/{opportunity_id}/reports", json=body, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()["report_id"]


def _review(client: TestClient, admin: dict[str, str], report_id: int, **body: Any) -> None:
    response = client.post(f"{API}/admin/reports/{report_id}/review", json=body, headers=admin)
    assert response.status_code == 200, response.text


@pytest.fixture
def taken_down(
    client: TestClient, contributor: dict[str, str], jordan: dict[str, str], admin: dict[str, str]
) -> None:
    """Alex and Jordan report opportunity 1; the admin upholds Alex's, which upholds both."""
    alex = _report(client, contributor, 1, reason="misleading_terms", details=ALEX_WORDS)
    _report(client, jordan, 1, reason="scam_or_spam")
    _review(client, admin, alex, decision="upheld", reason="The advertised pay is not real.")


@pytest.mark.usefixtures("taken_down")
def test_the_owner_learns_when_and_why_but_not_who(
    client: TestClient, bakery: dict[str, str]
) -> None:
    response = client.get(f"{API}/opportunities/1/takedown", headers=bakery)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["opportunity_id"] == 1
    assert body["admin_reason"] == "The advertised pay is not real."
    assert body["reasons"] == ["misleading_terms", "scam_or_spam"]
    assert body["taken_down_at"].endswith("Z")
    assert set(body) == {"opportunity_id", "taken_down_at", "admin_reason", "reasons"}
    for leak in (ALEX_WORDS, "Alex", "Jordan", "reporter", "details"):
        assert leak not in response.text


@pytest.mark.usefixtures("taken_down")
def test_reports_after_a_takedown_are_refused_and_categories_stay_distinct(
    client: TestClient, bakery: dict[str, str], sam: dict[str, str]
) -> None:
    # Sam can't report a cancelled opportunity, so the categories stay as they were.
    assert _error(
        client.post(f"{API}/opportunities/1/reports", json={"reason": "other"}, headers=sam), 409
    ) == ("OPPORTUNITY_CANCELLED")
    reasons = client.get(f"{API}/opportunities/1/takedown", headers=bakery).json()["reasons"]
    assert len(reasons) == len(set(reasons))


@pytest.mark.usefixtures("taken_down")
def test_only_the_owner_sees_it(
    client: TestClient,
    events_org: dict[str, str],
    contributor: dict[str, str],
    admin: dict[str, str],
) -> None:
    url = f"{API}/opportunities/1/takedown"
    assert _error(client.get(url, headers=events_org), 404) == "OPPORTUNITY_NOT_FOUND"
    for headers in (contributor, admin):
        assert _error(client.get(url, headers=headers), 403) == "ROLE_FORBIDDEN"
    assert _error(client.get(url), 401) == "AUTH_REQUIRED"


def test_not_taken_down(
    client: TestClient, bakery: dict[str, str], contributor: dict[str, str], admin: dict[str, str]
) -> None:
    # No reports at all.
    assert _error(client.get(f"{API}/opportunities/1/takedown", headers=bakery), 404) == (
        "TAKEDOWN_NOT_FOUND"
    )
    # A dismissed report isn't a takedown.
    report = _report(client, contributor, 1, reason="other")
    _review(client, admin, report, decision="dismissed")
    assert _error(client.get(f"{API}/opportunities/1/takedown", headers=bakery), 404) == (
        "TAKEDOWN_NOT_FOUND"
    )
    assert _error(client.get(f"{API}/opportunities/9999/takedown", headers=bakery), 404) == (
        "OPPORTUNITY_NOT_FOUND"
    )


def test_the_old_takedown_report_path_is_gone(client: TestClient, bakery: dict[str, str]) -> None:
    response = client.get(f"{API}/opportunities/1/takedown-report", headers=bakery)
    assert response.status_code == 404


def test_admins_see_the_creator_of_each_reported_opportunity(
    client: TestClient, contributor: dict[str, str], admin: dict[str, str]
) -> None:
    _report(client, contributor, 1, reason="other")

    [item] = client.get(f"{API}/admin/reports", headers=admin).json()["items"]

    assert item["creator"] == {"user_id": 2, "full_name": "Priya Nair"}
    assert item["reporter"]["full_name"] == "Alex Chen"
