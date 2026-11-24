"""Applying, listing, deciding and withdrawing against the seeded test DB (ADR 0006).

Seed facts relied on (db/init/002_seed.sql; "now" is frozen at 2026-10-16 12:00 UTC):
- #1 bakery (org 1), open, limit 2;  #2 bakery, open, limit 1
- #8 YYC events (org 3), open;  #10 food bank, open but past its deadline
- #11 closed;  #14 bakery draft
- contributors: alex (5), jordan (6), sam (7); no applications are seeded
"""

import json
import threading
from datetime import datetime
from typing import Any

import pymysql
import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.fakes import FakePublisher

OPPS = "/api/v1/opportunities"
APPS = "/api/v1/applications"


def _apply(
    client: TestClient,
    headers: dict[str, str],
    opportunity_id: int,
    files: dict[str, Any] | None = None,
    **fields: str,
) -> Any:
    """Apply as the browser does: a multipart form (motivation, application_details as
    JSON text, optional resume PDF)."""
    return client.post(
        f"{OPPS}/{opportunity_id}/applications", data=fields, files=files, headers=headers
    )


def _applied(client: TestClient, headers: dict[str, str], opportunity_id: int) -> int:
    response = _apply(client, headers, opportunity_id)
    assert response.status_code == 201, response.text
    return response.json()["application_id"]


def _error(response: Any, status: int) -> str:
    assert response.status_code == status, response.text
    return response.json()["error"]["code"]


# --- applying -----------------------------------------------------------------


def test_contributor_applies_and_the_creator_is_told(
    client: TestClient, contributor: dict[str, str], publisher: FakePublisher
) -> None:
    response = client.post(
        f"{OPPS}/1/applications",
        data={"motivation": "  I type fast and love bread.  "},
        headers={**contributor, "X-Request-ID": "apply-1"},
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "pending"
    assert body["motivation"] == "I type fast and love bread."
    assert body["submitted_at"] == "2026-10-16T12:00:00Z"
    assert body["decided_at"] is None
    assert body["opportunity"]["opportunity_id"] == 1
    assert body["opportunity"]["organization"]["name"] == "Maple Street Bakery"
    assert body["applicant"]["user_id"] == 5
    assert body["applicant"]["full_name"] == "Alex Chen"
    assert "email" not in body["applicant"]

    [event] = publisher.events
    assert event.event_type == "APPLICATION_SUBMITTED"
    assert event.correlation_id == "apply-1"
    assert event.payload == {
        "application_id": body["application_id"],
        "opportunity_id": 1,
        "organization_id": 1,
        "opportunity_title": "Digitize paper recipe archive",
        "contributor_id": 5,
        "contributor_name": "Alex Chen",
    }


def test_motivation_is_optional_and_bad_details_are_rejected(
    client: TestClient, contributor: dict[str, str]
) -> None:
    assert _apply(client, contributor, 1).json()["motivation"] is None
    assert (
        _error(_apply(client, contributor, 8, application_details="not json"), 422)
        == "VALIDATION_ERROR"
    )


def test_application_details_are_kept(client: TestClient, contributor: dict[str, str]) -> None:
    response = _apply(
        client, contributor, 1, application_details=json.dumps({"phone": "403-555-0101"})
    )

    assert response.status_code == 201, response.text
    assert response.json()["application_details"] == {"phone": "403-555-0101"}


def test_a_resume_can_be_sent_with_the_application(
    client: TestClient, contributor: dict[str, str]
) -> None:
    pdf = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"
    response = _apply(client, contributor, 1, files={"resume": ("cv.pdf", pdf, "application/pdf")})

    assert response.status_code == 201, response.text
    assert response.json()["applicant"]["has_resume"] is True


def test_an_application_resume_must_be_a_pdf(
    client: TestClient, contributor: dict[str, str]
) -> None:
    response = _apply(client, contributor, 1, files={"resume": ("cv.txt", b"hello", "text/plain")})

    assert _error(response, 415) == "UNSUPPORTED_FILE_TYPE"


def test_applying_twice_is_409_and_points_to_the_first_application(
    client: TestClient, contributor: dict[str, str], publisher: FakePublisher
) -> None:
    first = _applied(client, contributor, 1)

    response = _apply(client, contributor, 1)

    assert _error(response, 409) == "APPLICATION_DUPLICATE"
    assert response.json()["error"]["details"] == {"application_id": first}
    assert len(publisher.events) == 1


def test_withdrawn_contributor_can_apply_again_on_the_same_application(
    client: TestClient, contributor: dict[str, str]
) -> None:
    application_id = _applied(client, contributor, 1)
    client.post(f"{APPS}/{application_id}/withdraw", headers=contributor)

    response = _apply(client, contributor, 1, motivation="Second try")

    assert response.status_code == 201, response.text
    body = response.json()
    # The row is reused (one application per contributor and opportunity).
    assert body["application_id"] == application_id
    assert body["status"] == "pending"
    assert body["motivation"] == "Second try"


def test_applicant_limit_counts_pending_and_accepted(
    client: TestClient, contributor: dict[str, str], jordan: dict[str, str]
) -> None:
    _applied(client, contributor, 2)  # #2 has one place

    assert _error(_apply(client, jordan, 2), 409) == "APPLICANT_LIMIT_REACHED"


def test_withdrawing_frees_the_place(
    client: TestClient, contributor: dict[str, str], jordan: dict[str, str]
) -> None:
    application_id = _applied(client, contributor, 2)
    client.post(f"{APPS}/{application_id}/withdraw", headers=contributor)

    assert _apply(client, jordan, 2).status_code == 201


def test_rejecting_frees_the_place(
    client: TestClient, contributor: dict[str, str], jordan: dict[str, str], bakery: dict[str, str]
) -> None:
    application_id = _applied(client, contributor, 2)
    client.post(f"{APPS}/{application_id}/decision", json={"decision": "rejected"}, headers=bakery)

    assert _apply(client, jordan, 2).status_code == 201


def test_cannot_apply_after_the_deadline(client: TestClient, contributor: dict[str, str]) -> None:
    assert _error(_apply(client, contributor, 10), 409) == "APPLICATION_DEADLINE_PASSED"


def test_cannot_apply_to_a_closed_opportunity(
    client: TestClient, contributor: dict[str, str]
) -> None:
    assert _error(_apply(client, contributor, 11), 409) == "OPPORTUNITY_NOT_OPEN"


def test_drafts_and_unknown_opportunities_are_404(
    client: TestClient, contributor: dict[str, str]
) -> None:
    assert _error(_apply(client, contributor, 14), 404) == "OPPORTUNITY_NOT_FOUND"
    assert _error(_apply(client, contributor, 9999), 404) == "OPPORTUNITY_NOT_FOUND"


def test_contributor_without_a_profile_cannot_apply(
    client: TestClient,
    sam: dict[str, str],
    seeded_db: pymysql.Connection,
    publisher: FakePublisher,
) -> None:
    with seeded_db.cursor() as cur:  # sign-up always creates one; remove it directly
        cur.execute("DELETE FROM contributor_profile WHERE user_id = 7")

    assert _error(_apply(client, sam, 8), 409) == "CONTRIBUTOR_PROFILE_REQUIRED"
    assert publisher.events == []


def test_only_contributors_can_apply(client: TestClient, bakery: dict[str, str]) -> None:
    assert _error(_apply(client, bakery, 8), 403) == "ROLE_FORBIDDEN"
    assert _error(client.post(f"{OPPS}/8/applications", json={}), 401) == "AUTH_REQUIRED"


def test_two_contributors_racing_for_the_last_place(
    client: TestClient, contributor: dict[str, str], jordan: dict[str, str]
) -> None:
    """Both requests run at once against the real database: exactly one gets the
    single place on #2, the other gets 409 (from the service check or the trigger)."""
    start = threading.Barrier(2)
    results: list[Any] = []

    def run(headers: dict[str, str]) -> None:
        own_client = TestClient(app)  # one client per thread
        start.wait()
        results.append(_apply(own_client, headers, 2))

    threads = [threading.Thread(target=run, args=(h,)) for h in (contributor, jordan)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert sorted(r.status_code for r in results) == [201, 409]
    [refused] = [r for r in results if r.status_code == 409]
    assert refused.json()["error"]["code"] == "APPLICANT_LIMIT_REACHED"


# --- listing and viewing ------------------------------------------------------


def test_contributor_sees_only_their_own_applications(
    client: TestClient, contributor: dict[str, str], jordan: dict[str, str]
) -> None:
    mine = {_applied(client, contributor, 1), _applied(client, contributor, 8)}
    _applied(client, jordan, 1)

    response = client.get(f"{APPS}/mine", headers=contributor)

    assert response.status_code == 200
    assert {a["application_id"] for a in response.json()["items"]} == mine
    assert response.json()["total"] == 2


def test_my_applications_filter_by_status(client: TestClient, contributor: dict[str, str]) -> None:
    kept = _applied(client, contributor, 1)
    dropped = _applied(client, contributor, 8)
    client.post(f"{APPS}/{dropped}/withdraw", headers=contributor)

    pending = client.get(f"{APPS}/mine", params={"status": "pending"}, headers=contributor)

    assert [a["application_id"] for a in pending.json()["items"]] == [kept]


def test_creator_lists_applications_to_their_opportunity(
    client: TestClient,
    contributor: dict[str, str],
    jordan: dict[str, str],
    bakery: dict[str, str],
) -> None:
    _applied(client, contributor, 1)
    _applied(client, jordan, 1)
    _applied(client, jordan, 8)  # another organization's opportunity

    response = client.get(f"{OPPS}/1/applications", headers=bakery)

    assert response.status_code == 200
    items = response.json()["items"]
    assert {a["applicant"]["full_name"] for a in items} == {"Alex Chen", "Jordan Lee"}
    alex = next(a for a in items if a["applicant"]["user_id"] == 5)
    assert [s["code"] for s in alex["applicant"]["skills"]]  # skills come with the applicant


def test_only_the_owner_lists_an_opportunitys_applications(
    client: TestClient, events_org: dict[str, str], contributor: dict[str, str]
) -> None:
    assert _error(client.get(f"{OPPS}/1/applications", headers=events_org), 403) == (
        "NOT_OPPORTUNITY_OWNER"
    )
    assert _error(client.get(f"{OPPS}/14/applications", headers=events_org), 404) == (
        "OPPORTUNITY_NOT_FOUND"
    )
    assert _error(client.get(f"{OPPS}/1/applications", headers=contributor), 403) == (
        "ROLE_FORBIDDEN"
    )


def test_creator_lists_applications_received_across_their_opportunities(
    client: TestClient,
    contributor: dict[str, str],
    jordan: dict[str, str],
    bakery: dict[str, str],
    events_org: dict[str, str],
) -> None:
    first = _applied(client, contributor, 1)
    second = _applied(client, jordan, 2)
    _applied(client, jordan, 8)  # YYC's opportunity

    bakery_page = client.get(f"{APPS}/received", headers=bakery).json()
    yyc_page = client.get(f"{APPS}/received", headers=events_org).json()

    assert [a["application_id"] for a in bakery_page["items"]] == [second, first]  # newest first
    assert bakery_page["total"] == 2
    assert [a["opportunity"]["opportunity_id"] for a in yyc_page["items"]] == [8]


def test_received_applications_filter_by_opportunity_and_status(
    client: TestClient,
    contributor: dict[str, str],
    jordan: dict[str, str],
    bakery: dict[str, str],
) -> None:
    on_1 = _applied(client, contributor, 1)
    _applied(client, jordan, 1)
    on_2 = _applied(client, jordan, 2)
    client.post(f"{APPS}/{on_2}/decision", json={"decision": "accepted"}, headers=bakery)

    def ids(query: str) -> list[int]:
        response = client.get(f"{APPS}/received?{query}", headers=bakery)
        assert response.status_code == 200, response.text
        return [a["application_id"] for a in response.json()["items"]]

    assert len(ids("opportunity_id=1")) == 2
    assert ids("status=accepted") == [on_2]
    assert ids("opportunity_id=1&limit=1&offset=1") == [on_1]
    assert ids("opportunity_id=8") == []  # someone else's opportunity matches nothing
    assert ids("opportunity_id=9999") == []


def test_only_creators_list_received_applications(
    client: TestClient, contributor: dict[str, str], bakery: dict[str, str]
) -> None:
    assert _error(client.get(f"{APPS}/received", headers=contributor), 403) == "ROLE_FORBIDDEN"
    assert _error(client.get(f"{APPS}/received"), 401) == "AUTH_REQUIRED"
    bad = client.get(f"{APPS}/received?opportunity_id=0", headers=bakery)
    assert _error(bad, 422) == "VALIDATION_ERROR"


def test_an_application_is_visible_only_to_its_two_parties(
    client: TestClient,
    contributor: dict[str, str],
    jordan: dict[str, str],
    bakery: dict[str, str],
    events_org: dict[str, str],
) -> None:
    application_id = _applied(client, contributor, 1)
    url = f"{APPS}/{application_id}"

    assert client.get(url, headers=contributor).status_code == 200
    assert client.get(url, headers=bakery).status_code == 200
    assert _error(client.get(url, headers=jordan), 404) == "APPLICATION_NOT_FOUND"
    assert _error(client.get(url, headers=events_org), 404) == "APPLICATION_NOT_FOUND"
    assert _error(client.get(f"{APPS}/9999", headers=bakery), 404) == "APPLICATION_NOT_FOUND"


# --- deciding -----------------------------------------------------------------


def test_creator_accepts_and_the_contributor_is_told(
    client: TestClient,
    contributor: dict[str, str],
    bakery: dict[str, str],
    publisher: FakePublisher,
) -> None:
    application_id = _applied(client, contributor, 1)

    response = client.post(
        f"{APPS}/{application_id}/decision", json={"decision": "accepted"}, headers=bakery
    )

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "accepted"
    assert response.json()["decided_at"] == "2026-10-16T12:00:00Z"
    event = publisher.events[-1]
    assert event.event_type == "APPLICATION_DECIDED"
    assert event.payload == {
        "application_id": application_id,
        "opportunity_id": 1,
        "opportunity_title": "Digitize paper recipe archive",
        "contributor_id": 5,
        "decision": "accepted",
    }


def test_each_application_is_decided_once(
    client: TestClient, contributor: dict[str, str], bakery: dict[str, str]
) -> None:
    application_id = _applied(client, contributor, 1)
    url = f"{APPS}/{application_id}/decision"
    client.post(url, json={"decision": "rejected"}, headers=bakery)

    again = client.post(url, json={"decision": "accepted"}, headers=bakery)

    assert _error(again, 409) == "APPLICATION_NOT_PENDING"


def test_withdrawn_application_cannot_be_decided(
    client: TestClient, contributor: dict[str, str], bakery: dict[str, str]
) -> None:
    application_id = _applied(client, contributor, 1)
    client.post(f"{APPS}/{application_id}/withdraw", headers=contributor)

    response = client.post(
        f"{APPS}/{application_id}/decision", json={"decision": "accepted"}, headers=bakery
    )

    assert _error(response, 409) == "APPLICATION_NOT_PENDING"


def test_only_the_owning_creator_decides(
    client: TestClient,
    contributor: dict[str, str],
    events_org: dict[str, str],
    publisher: FakePublisher,
) -> None:
    application_id = _applied(client, contributor, 1)
    url = f"{APPS}/{application_id}/decision"

    assert _error(client.post(url, json={"decision": "accepted"}, headers=events_org), 404) == (
        "APPLICATION_NOT_FOUND"
    )
    assert _error(client.post(url, json={"decision": "accepted"}, headers=contributor), 403) == (
        "ROLE_FORBIDDEN"
    )
    assert [e.event_type for e in publisher.events] == ["APPLICATION_SUBMITTED"]


def test_decision_must_be_accepted_or_rejected(
    client: TestClient, contributor: dict[str, str], bakery: dict[str, str]
) -> None:
    application_id = _applied(client, contributor, 1)

    response = client.post(
        f"{APPS}/{application_id}/decision", json={"decision": "withdrawn"}, headers=bakery
    )

    assert _error(response, 422) == "VALIDATION_ERROR"


def test_deciding_is_allowed_after_the_deadline(
    client: TestClient,
    contributor: dict[str, str],
    bakery: dict[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    application_id = _applied(client, contributor, 2)  # #2 closes 2026-11-05
    monkeypatch.setattr(
        "app.services.application_service.utcnow", lambda: datetime(2026, 11, 10, 9, 0)
    )

    response = client.post(
        f"{APPS}/{application_id}/decision", json={"decision": "accepted"}, headers=bakery
    )

    assert response.status_code == 200, response.text


# --- withdrawing --------------------------------------------------------------


def test_contributor_withdraws_and_the_creator_is_told(
    client: TestClient,
    contributor: dict[str, str],
    bakery: dict[str, str],
    publisher: FakePublisher,
) -> None:
    pending = _applied(client, contributor, 1)
    accepted = _applied(client, contributor, 2)
    client.post(f"{APPS}/{accepted}/decision", json={"decision": "accepted"}, headers=bakery)

    for application_id, opportunity_id, title, previous in (
        (pending, 1, "Digitize paper recipe archive", "pending"),
        (accepted, 2, "Inventory spreadsheet cleanup", "accepted"),
    ):
        response = client.post(
            f"{APPS}/{application_id}/withdraw",
            headers={**contributor, "X-Request-ID": f"withdraw-{application_id}"},
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "withdrawn"

        event = publisher.events[-1]
        assert event.event_type == "APPLICATION_WITHDRAWN"
        assert event.correlation_id == f"withdraw-{application_id}"
        assert event.payload == {
            "application_id": application_id,
            "opportunity_id": opportunity_id,
            "organization_id": 1,
            "opportunity_title": title,
            "contributor_id": 5,
            "contributor_name": "Alex Chen",
            "previous_status": previous,
        }


def test_rejected_or_withdrawn_applications_cannot_be_withdrawn(
    client: TestClient,
    contributor: dict[str, str],
    bakery: dict[str, str],
    publisher: FakePublisher,
) -> None:
    rejected = _applied(client, contributor, 1)
    client.post(f"{APPS}/{rejected}/decision", json={"decision": "rejected"}, headers=bakery)
    withdrawn = _applied(client, contributor, 8)
    client.post(f"{APPS}/{withdrawn}/withdraw", headers=contributor)
    sent = len(publisher.events)

    for application_id in (rejected, withdrawn):
        response = client.post(f"{APPS}/{application_id}/withdraw", headers=contributor)
        assert _error(response, 409) == "APPLICATION_NOT_ACTIVE"
    assert len(publisher.events) == sent  # a refused withdrawal sends nothing


def test_cannot_withdraw_once_work_is_submitted(
    client: TestClient,
    contributor: dict[str, str],
    bakery: dict[str, str],
    seeded_db: pymysql.Connection,
) -> None:
    application_id = _applied(client, contributor, 1)
    client.post(f"{APPS}/{application_id}/decision", json={"decision": "accepted"}, headers=bakery)
    with seeded_db.cursor() as cur:  # no submission endpoint yet; insert it directly
        cur.execute(
            "INSERT INTO work_submission (application_id, description, hours_claimed) "
            "VALUES (%s, 'Scanned all cards.', 18)",
            (application_id,),
        )

    response = client.post(f"{APPS}/{application_id}/withdraw", headers=contributor)

    assert _error(response, 409) == "WORK_ALREADY_SUBMITTED"


def test_only_the_applicant_withdraws(
    client: TestClient,
    contributor: dict[str, str],
    jordan: dict[str, str],
    bakery: dict[str, str],
    publisher: FakePublisher,
) -> None:
    application_id = _applied(client, contributor, 1)
    url = f"{APPS}/{application_id}/withdraw"

    assert _error(client.post(url, headers=jordan), 404) == "APPLICATION_NOT_FOUND"
    assert _error(client.post(url, headers=bakery), 403) == "ROLE_FORBIDDEN"
    assert [e.event_type for e in publisher.events] == ["APPLICATION_SUBMITTED"]
