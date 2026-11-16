"""Closing and cancelling published opportunities (ADR 0011), against the seeded test DB.

Seed facts relied on (db/init/002_seed.sql; "now" is frozen at 2026-10-16 12:00 UTC):
- bakery (org 1): #1 open (limit 2), #2 open (limit 1), #4 open, #14 draft
- YYC events (org 3): #8 open
- food bank (org 2): #11 closed
- contributors: alex (5), jordan (6), sam (7); no applications are seeded
"""

from typing import Any

import pymysql
from fastapi.testclient import TestClient

from tests.fakes import FakePublisher

OPPS = "/api/v1/opportunities"
APPS = "/api/v1/applications"


def _error(response: Any, status: int) -> str:
    assert response.status_code == status, response.text
    return response.json()["error"]["code"]


def _applied(client: TestClient, headers: dict[str, str], opportunity_id: int) -> int:
    response = client.post(f"{OPPS}/{opportunity_id}/applications", json={}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["application_id"]


# --- closing ------------------------------------------------------------------


def test_closing_stops_new_applications_but_not_decisions(
    client: TestClient,
    contributor: dict[str, str],
    jordan: dict[str, str],
    bakery: dict[str, str],
    publisher: FakePublisher,
) -> None:
    pending = _applied(client, contributor, 1)
    sent = len(publisher.events)

    response = client.post(f"{OPPS}/1/close", headers=bakery)

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "closed"
    assert len(publisher.events) == sent  # closing notifies nobody
    applying = client.post(f"{OPPS}/1/applications", json={}, headers=jordan)
    assert _error(applying, 409) == "OPPORTUNITY_NOT_OPEN"
    decided = client.post(
        f"{APPS}/{pending}/decision", json={"decision": "accepted"}, headers=bakery
    )
    assert decided.status_code == 200, decided.text
    assert decided.json()["opportunity"]["status"] == "closed"


def test_only_open_opportunities_can_be_closed(
    client: TestClient, bakery: dict[str, str], seeded_db: pymysql.Connection
) -> None:
    client.post(f"{OPPS}/1/close", headers=bakery)
    with seeded_db.cursor() as cur:
        cur.execute("UPDATE opportunity SET status = 'cancelled' WHERE opportunity_id = 2")
    seeded_db.commit()

    for opportunity_id in (1, 2, 14):  # closed, cancelled, draft
        response = client.post(f"{OPPS}/{opportunity_id}/close", headers=bakery)
        assert _error(response, 409) == "OPPORTUNITY_NOT_OPEN"


def test_a_closed_opportunity_leaves_the_public_list_but_stays_readable(
    client: TestClient, bakery: dict[str, str]
) -> None:
    client.post(f"{OPPS}/1/close", headers=bakery)

    listed = client.get(f"{OPPS}?limit=100").json()["items"]
    assert 1 not in [o["opportunity_id"] for o in listed]
    assert client.get(f"{OPPS}/1").json()["status"] == "closed"


# --- cancelling ---------------------------------------------------------------


def test_cancelling_keeps_statuses_and_tells_applicants(
    client: TestClient,
    contributor: dict[str, str],
    jordan: dict[str, str],
    bakery: dict[str, str],
    publisher: FakePublisher,
) -> None:
    pending = _applied(client, contributor, 1)
    accepted = _applied(client, jordan, 1)
    client.post(f"{APPS}/{accepted}/decision", json={"decision": "accepted"}, headers=bakery)

    response = client.post(
        f"{OPPS}/1/cancel", headers={**bakery, "X-Request-ID": "cancel-1"}
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "cancelled"
    event = publisher.events[-1]
    assert event.event_type == "OPPORTUNITY_CANCELLED"
    assert event.correlation_id == "cancel-1"
    assert event.payload == {
        "opportunity_id": 1,
        "organization_id": 1,
        "title": "Digitize paper recipe archive",
    }
    for application_id, status in ((pending, "pending"), (accepted, "accepted")):
        body = client.get(f"{APPS}/{application_id}", headers=bakery).json()
        assert body["status"] == status
        assert body["opportunity"]["status"] == "cancelled"


def test_a_closed_opportunity_can_be_cancelled(
    client: TestClient, bakery: dict[str, str]
) -> None:
    client.post(f"{OPPS}/1/close", headers=bakery)

    response = client.post(f"{OPPS}/1/cancel", headers=bakery)

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "cancelled"


def test_applications_to_a_cancelled_opportunity_cant_be_decided(
    client: TestClient, contributor: dict[str, str], bakery: dict[str, str]
) -> None:
    pending = _applied(client, contributor, 1)
    client.post(f"{OPPS}/1/cancel", headers=bakery)

    response = client.post(
        f"{APPS}/{pending}/decision", json={"decision": "accepted"}, headers=bakery
    )

    assert _error(response, 409) == "OPPORTUNITY_CANCELLED"


def test_applicants_can_still_withdraw_after_a_cancel(
    client: TestClient, contributor: dict[str, str], bakery: dict[str, str]
) -> None:
    pending = _applied(client, contributor, 1)
    client.post(f"{OPPS}/1/cancel", headers=bakery)

    response = client.post(f"{APPS}/{pending}/withdraw", headers=contributor)

    assert response.status_code == 200, response.text


def test_drafts_and_cancelled_opportunities_cant_be_cancelled(
    client: TestClient, bakery: dict[str, str], publisher: FakePublisher
) -> None:
    client.post(f"{OPPS}/1/cancel", headers=bakery)
    sent = len(publisher.events)

    draft = client.post(f"{OPPS}/14/cancel", headers=bakery)
    again = client.post(f"{OPPS}/1/cancel", headers=bakery)

    assert _error(draft, 409) == "OPPORTUNITY_NOT_PUBLISHED"
    assert _error(again, 409) == "OPPORTUNITY_CANCELLED"
    assert len(publisher.events) == sent


def test_cannot_cancel_once_work_is_submitted(
    client: TestClient,
    contributor: dict[str, str],
    bakery: dict[str, str],
    seeded_db: pymysql.Connection,
    publisher: FakePublisher,
) -> None:
    application_id = _applied(client, contributor, 1)
    client.post(f"{APPS}/{application_id}/decision", json={"decision": "accepted"}, headers=bakery)
    with seeded_db.cursor() as cur:  # no submission endpoint yet; insert it directly
        cur.execute(
            "INSERT INTO work_submission (application_id, description, hours_claimed) "
            "VALUES (%s, 'Scanned all cards.', 18)",
            (application_id,),
        )
    seeded_db.commit()
    sent = len(publisher.events)

    response = client.post(f"{OPPS}/1/cancel", headers=bakery)

    assert _error(response, 409) == "WORK_ALREADY_SUBMITTED"
    assert client.get(f"{OPPS}/1").json()["status"] == "open"
    assert len(publisher.events) == sent


# --- who may -----------------------------------------------------------------


def test_only_the_owner_closes_or_cancels(
    client: TestClient,
    events_org: dict[str, str],
    contributor: dict[str, str],
) -> None:
    for action in ("close", "cancel"):
        url = f"{OPPS}/1/{action}"
        assert _error(client.post(url, headers=events_org), 403) == "NOT_OPPORTUNITY_OWNER"
        assert _error(client.post(url, headers=contributor), 403) == "ROLE_FORBIDDEN"
        assert _error(client.post(url), 401) == "AUTH_REQUIRED"
        hidden = client.post(f"{OPPS}/14/{action}", headers=events_org)  # bakery's draft
        assert _error(hidden, 404) == "OPPORTUNITY_NOT_FOUND"
