"""Opportunity creation, publishing, search, filter and sort against the seeded test DB.

Seed facts relied on (db/init/002_seed.sql):
- 12 'open' rows, of which #10 is past its deadline -> 11 publicly listed
- #11 is closed, #14 (bakery, incomplete) and #15 (events org, complete) are drafts
"""

from typing import Any

from fastapi.testclient import TestClient

from tests.fakes import FakePublisher

URL = "/api/v1/opportunities"
PUBLIC_IDS = {1, 2, 3, 4, 5, 6, 7, 8, 9, 12, 13}


def _ids(response: Any) -> list[int]:
    assert response.status_code == 200, response.text
    return [o["opportunity_id"] for o in response.json()["items"]]


def _complete_body(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "title": "Catalogue bread recipes",
        "description": "Type up recipes into a shared document.",
        "category": "knowledge",
        "skills": ["data-entry", "spreadsheets"],
        "requirements": "Careful typing.",
        "work_mode": "remote",
        "start_date": "2027-03-01",
        "end_date": "2027-03-20",
        "expected_hours": 8,
        "compensation_type": "paid",
        "compensation_amount": 160,
        "applicant_limit": 2,
        "application_deadline": "2027-02-15T23:59:00-07:00",
        "working_conditions": "Remote, flexible.",
        "safety_information": "Remote work; no hazards.",
        "accessibility_details": "Any assistive technology is fine.",
    }
    body.update(overrides)
    return body


# --- browsing -----------------------------------------------------------------


def test_public_list_shows_only_open_opportunities_before_their_deadline(
    client: TestClient,
) -> None:
    response = client.get(URL, params={"limit": 100})

    assert set(_ids(response)) == PUBLIC_IDS
    assert response.json()["total"] == 11
    assert all(o["status"] == "open" for o in response.json()["items"])


def test_pagination(client: TestClient) -> None:
    first = client.get(URL, params={"limit": 4, "offset": 0})
    second = client.get(URL, params={"limit": 4, "offset": 4})

    assert first.json()["total"] == 11
    assert len(_ids(first)) == 4
    assert set(_ids(first)).isdisjoint(_ids(second))


def test_search_is_case_insensitive_across_title_description_and_organization(
    client: TestClient,
) -> None:
    # #2 has it in the title, #1 in the description
    assert set(_ids(client.get(URL, params={"q": "SPREADSHEET"}))) == {1, 2}
    # "Food Bank" only appears in the organization name for #5, #6, #7
    assert set(_ids(client.get(URL, params={"q": "food bank"}))) == {5, 6, 7}


def test_search_treats_wildcards_literally(client: TestClient) -> None:
    assert _ids(client.get(URL, params={"q": "%"})) == []


def test_filter_by_category(client: TestClient) -> None:
    ids = _ids(client.get(URL, params={"category": "knowledge", "limit": 100}))
    assert set(ids) == {1, 2, 3, 6, 7, 9}


def test_filter_by_any_of_several_skills(client: TestClient) -> None:
    ids = _ids(client.get(URL, params=[("skill", "photography"), ("skill", "translation")]))
    assert set(ids) == {3, 7, 12}


def test_filter_by_work_mode_and_compensation(client: TestClient) -> None:
    ids = _ids(client.get(URL, params={"work_mode": "remote", "compensation_type": "unpaid"}))
    assert ids == [7]


def test_filter_by_hours_range(client: TestClient) -> None:
    ids = _ids(client.get(URL, params={"min_hours": 20, "max_hours": 25, "limit": 100}))
    assert set(ids) == {1, 5, 9}


def test_filter_by_deadline_before(client: TestClient) -> None:
    ids = _ids(client.get(URL, params={"deadline_before": "2026-11-13T00:00:00Z"}))
    assert ids == [2, 12, 3]


def test_invalid_hours_range_is_422(client: TestClient) -> None:
    response = client.get(URL, params={"min_hours": 10, "max_hours": 5})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_sort_by_deadline_both_directions(client: TestClient) -> None:
    ascending = _ids(client.get(URL, params={"sort": "deadline", "limit": 100}))
    descending = _ids(client.get(URL, params={"sort": "-deadline", "limit": 100}))

    assert ascending[:3] == [2, 12, 3]
    assert descending[0] == 7
    assert descending == list(reversed(ascending))


def test_sort_by_hours_newest_and_compensation(client: TestClient) -> None:
    assert _ids(client.get(URL, params={"sort": "hours", "limit": 1})) == [12]
    assert _ids(client.get(URL, params={"sort": "-hours", "limit": 1})) == [6]
    assert _ids(client.get(URL, params={"sort": "newest", "limit": 1})) == [13]
    assert _ids(client.get(URL, params={"sort": "-compensation", "limit": 1})) == [9]


def test_unknown_sort_is_422(client: TestClient) -> None:
    assert client.get(URL, params={"sort": "random"}).status_code == 422


def test_reference_lists(client: TestClient) -> None:
    categories = client.get("/api/v1/categories").json()
    skills = client.get("/api/v1/skills").json()

    assert {c["code"] for c in categories} == {"knowledge", "community"}
    assert len(skills) == 12


# --- viewing one --------------------------------------------------------------


def test_draft_is_hidden_from_everyone_but_its_owner(
    client: TestClient, bakery: dict[str, str], events_org: dict[str, str]
) -> None:
    assert client.get(f"{URL}/14").status_code == 404
    assert client.get(f"{URL}/14", headers=events_org).status_code == 404
    assert client.get(f"{URL}/14", headers=bakery).status_code == 200


def test_closed_opportunity_is_viewable_but_not_listed(client: TestClient) -> None:
    assert client.get(f"{URL}/11").json()["status"] == "closed"
    assert 11 not in _ids(client.get(URL, params={"limit": 100}))


def test_my_opportunities_include_drafts_and_filter_by_status(
    client: TestClient, bakery: dict[str, str]
) -> None:
    assert set(_ids(client.get(f"{URL}/mine", headers=bakery))) == {1, 2, 3, 4, 14}
    drafts = client.get(f"{URL}/mine", params={"status": "draft"}, headers=bakery)
    assert _ids(drafts) == [14]


def test_my_opportunities_is_creator_only(client: TestClient, contributor: dict[str, str]) -> None:
    assert client.get(f"{URL}/mine", headers=contributor).status_code == 403


# --- creating -----------------------------------------------------------------


def test_creator_creates_a_draft_for_their_own_organization(
    client: TestClient, bakery: dict[str, str], publisher: FakePublisher
) -> None:
    response = client.post(URL, json=_complete_body(), headers=bakery)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "draft"
    assert body["organization"]["organization_id"] == 1
    assert body["category"]["code"] == "knowledge"
    assert [s["code"] for s in body["skills"]] == ["data-entry", "spreadsheets"]
    # -07:00 input is stored and returned in UTC
    assert body["application_deadline"] == "2027-02-16T06:59:00Z"
    assert body["published_at"] is None
    assert publisher.events == []
    assert body["opportunity_id"] not in _ids(client.get(URL, params={"limit": 100}))


def test_draft_can_be_saved_incomplete(client: TestClient, bakery: dict[str, str]) -> None:
    body = {"title": "Idea", "description": "Fill in later", "category": "community"}
    assert client.post(URL, json=body, headers=bakery).status_code == 201


def test_contributor_cannot_create(client: TestClient, contributor: dict[str, str]) -> None:
    response = client.post(URL, json=_complete_body(), headers=contributor)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ROLE_FORBIDDEN"


def test_anonymous_cannot_create(client: TestClient) -> None:
    assert client.post(URL, json=_complete_body()).status_code == 401


def test_unknown_category_and_skill_are_422(client: TestClient, bakery: dict[str, str]) -> None:
    bad_category = client.post(URL, json=_complete_body(category="music"), headers=bakery)
    bad_skill = client.post(URL, json=_complete_body(skills=["juggling"]), headers=bakery)

    assert bad_category.json()["error"]["code"] == "UNKNOWN_CATEGORY"
    assert bad_skill.status_code == 422
    assert bad_skill.json()["error"]["details"] == {"unknown_skills": ["juggling"]}


def test_body_validation(client: TestClient, bakery: dict[str, str]) -> None:
    cases = [
        _complete_body(end_date="2027-02-01"),  # before start_date
        _complete_body(expected_hours=0),
        _complete_body(compensation_amount=-5),
        _complete_body(applicant_limit=0),
        _complete_body(application_deadline="2027-02-15T23:59:00"),  # no timezone
        _complete_body(unexpected="field"),
    ]
    for body in cases:
        assert client.post(URL, json=body, headers=bakery).status_code == 422, body


# --- editing and publishing ---------------------------------------------------


def test_publish_incomplete_draft_lists_missing_fields(
    client: TestClient, bakery: dict[str, str], publisher: FakePublisher
) -> None:
    response = client.post(f"{URL}/14/publish", headers=bakery)

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "OPPORTUNITY_INCOMPLETE"
    assert "safety_information" in error["details"]["missing_fields"]
    assert "compensation_amount" in error["details"]["missing_fields"]
    assert publisher.events == []


def test_complete_draft_after_patch_then_publish(
    client: TestClient, bakery: dict[str, str], publisher: FakePublisher
) -> None:
    patch = _complete_body()
    for key in ("title", "description", "category", "skills"):
        patch.pop(key)
    assert client.patch(f"{URL}/14", json=patch, headers=bakery).status_code == 200

    response = client.post(f"{URL}/14/publish", headers=bakery)

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "open"
    assert response.json()["published_at"] is not None
    assert 14 in _ids(client.get(URL, params={"limit": 100}))


def test_publish_emits_opportunity_created_after_commit(
    client: TestClient, events_org: dict[str, str], publisher: FakePublisher
) -> None:
    response = client.post(
        f"{URL}/15/publish", headers={**events_org, "X-Request-ID": "req-123"}
    )

    assert response.status_code == 200, response.text
    assert response.headers["X-Request-ID"] == "req-123"
    [event] = publisher.events
    assert event.event_type == "OPPORTUNITY_CREATED"
    assert event.routing_key == "opportunity.created"
    assert event.correlation_id == "req-123"
    assert event.payload == {
        "opportunity_id": 15,
        "organization_id": 3,
        "title": "Volunteer coordinator for spring market",
        "category_code": "community",
        "application_deadline": "2027-02-28T23:59:59Z",
        "skill_codes": ["customer-service", "event-setup"],
    }


def test_cannot_publish_twice(
    client: TestClient, events_org: dict[str, str], publisher: FakePublisher
) -> None:
    assert client.post(f"{URL}/15/publish", headers=events_org).status_code == 200
    again = client.post(f"{URL}/15/publish", headers=events_org)

    assert again.status_code == 409
    assert again.json()["error"]["code"] == "OPPORTUNITY_NOT_DRAFT"
    assert len(publisher.events) == 1


def test_published_opportunity_cannot_be_edited(
    client: TestClient, bakery: dict[str, str]
) -> None:
    response = client.patch(f"{URL}/1", json={"title": "Changed"}, headers=bakery)

    assert response.status_code == 409


def test_publish_rejects_a_past_deadline(client: TestClient, bakery: dict[str, str]) -> None:
    created = client.post(
        URL, json=_complete_body(application_deadline="2020-01-01T00:00:00Z"), headers=bakery
    ).json()

    response = client.post(f"{URL}/{created['opportunity_id']}/publish", headers=bakery)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "DEADLINE_PASSED"


def test_only_the_owner_can_edit_or_publish(
    client: TestClient, bakery: dict[str, str], events_org: dict[str, str]
) -> None:
    # someone else's draft looks like it does not exist
    assert client.post(f"{URL}/15/publish", headers=bakery).status_code == 404
    assert client.patch(f"{URL}/15", json={"title": "Mine now"}, headers=bakery).status_code == 404
    # someone else's public opportunity is visible, so changing it is forbidden
    response = client.patch(f"{URL}/8", json={"title": "Mine now"}, headers=bakery)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "NOT_OPPORTUNITY_OWNER"


def test_patch_cannot_null_required_fields(client: TestClient, bakery: dict[str, str]) -> None:
    response = client.patch(f"{URL}/14", json={"title": None}, headers=bakery)

    assert response.status_code == 422
