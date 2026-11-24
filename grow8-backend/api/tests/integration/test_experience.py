"""GET /contributors/me/experience: totals from v_contributor_verified_hours, the approved
work behind them, and the skills that work verified.

Alex Chen (`contributor`) applies to opportunity 1 of Maple Street Bakery (`bakery`), is
accepted and submits 6.5 hours. The test DB seeds no applications, so Alex starts at zero.
"""

from typing import Any

from fastapi.testclient import TestClient

EXPERIENCE = "/api/v1/contributors/me/experience"


def _submitted(client: TestClient, contributor: dict[str, str], creator: dict[str, str]) -> int:
    applied = client.post("/api/v1/opportunities/1/applications", data={}, headers=contributor)
    assert applied.status_code == 201, applied.text
    application_id = applied.json()["application_id"]
    decided = client.post(
        f"/api/v1/applications/{application_id}/decision",
        json={"decision": "accepted"},
        headers=creator,
    )
    assert decided.status_code == 200, decided.text
    submitted = client.post(
        f"/api/v1/applications/{application_id}/submission",
        data={"description": "Typed up 40 recipes.", "hours_claimed": "6.5"},
        headers=contributor,
    )
    assert submitted.status_code == 201, submitted.text
    return submitted.json()["submission_id"]


def _verify(client: TestClient, creator: dict[str, str], submission_id: int, **body: Any) -> None:
    response = client.post(
        f"/api/v1/submissions/{submission_id}/verification", json=body, headers=creator
    )
    assert response.status_code == 200, response.text


def test_a_new_contributor_has_no_verified_experience(
    client: TestClient, contributor: dict[str, str]
) -> None:
    response = client.get(EXPERIENCE, headers=contributor)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["verified_hours"] == "0.00"
    assert body["completed_opportunities"] == 0
    assert body["organizations"] == 0
    assert body["completed_work"] == []


def test_approved_work_counts_with_the_verified_hours_not_the_claimed_ones(
    client: TestClient, contributor: dict[str, str], bakery: dict[str, str]
) -> None:
    submission_id = _submitted(client, contributor, bakery)
    _verify(
        client, bakery, submission_id, decision="approved", verified_hours="5", comment="Thanks!"
    )

    body = client.get(EXPERIENCE, headers=contributor).json()

    assert body["verified_hours"] == "5.00"
    assert body["completed_opportunities"] == 1
    assert body["organizations"] == 1
    [work] = body["completed_work"]
    assert work["submission_id"] == submission_id
    assert work["opportunity"] == {"opportunity_id": 1, "title": "Digitize paper recipe archive"}
    assert work["organization"]["name"] == "Maple Street Bakery"
    assert work["verified_hours"] == "5.00"
    assert work["comment"] == "Thanks!"
    assert work["verified_at"].endswith("Z") or work["verified_at"].endswith("+00:00")
    # The opportunity's skills are now verified for Alex (v_contributor_skill).
    assert body["verified_skills"], body
    assert all(skill["verified_at"] for skill in body["verified_skills"])


def test_rejected_work_does_not_count(
    client: TestClient, contributor: dict[str, str], bakery: dict[str, str]
) -> None:
    submission_id = _submitted(client, contributor, bakery)
    _verify(client, bakery, submission_id, decision="rejected", comment="Not finished.")

    body = client.get(EXPERIENCE, headers=contributor).json()

    assert body["verified_hours"] == "0.00"
    assert body["completed_opportunities"] == 0
    assert body["completed_work"] == []


def test_the_totals_match_the_view(
    client: TestClient,
    contributor: dict[str, str],
    bakery: dict[str, str],
    seeded_db: Any,
) -> None:
    submission_id = _submitted(client, contributor, bakery)
    _verify(client, bakery, submission_id, decision="approved", verified_hours="6.5")

    body = client.get(EXPERIENCE, headers=contributor).json()
    with seeded_db.cursor() as cursor:
        cursor.execute(
            "SELECT verified_hours, completed_opportunities FROM v_contributor_verified_hours "
            "WHERE contributor_id = 5"
        )
        hours, completed = cursor.fetchone()

    assert body["verified_hours"] == f"{hours:.2f}"
    assert body["completed_opportunities"] == completed


def test_only_contributors_have_experience(client: TestClient, bakery: dict[str, str]) -> None:
    assert client.get(EXPERIENCE).status_code == 401
    forbidden = client.get(EXPERIENCE, headers=bakery)
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "ROLE_FORBIDDEN"
