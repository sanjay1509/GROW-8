"""The contributor's own profile and skills, and changing your name (ADR 0017).

Seeded: Alex Chen (user 5) lists spreadsheets, data-cleaning and web-basics; none are
verified, because 002_seed.sql has no applications. Opportunity 1 (Maple Street Bakery,
owned by Priya Nair, user 2) requires data-entry and spreadsheets."""

import threading
from collections.abc import Iterator
from typing import Any

import pymysql
import pytest
from fastapi.testclient import TestClient
from grow8_common.db import get_sessionmaker
from grow8_common.queries import find_matching_contributors
from sqlalchemy.orm import Session

from app.repositories import user_repository
from app.schemas.contributor_profile import ProfileUpdate
from app.services import contributor_profile_service

API = "/api/v1"
PROFILE = f"{API}/contributors/me/profile"
SKILLS = f"{API}/contributors/me/skills"
ME = f"{API}/auth/me"
ALEX = 5


def _ok(response: Any) -> dict:
    assert response.status_code == 200, response.text
    return response.json()


def _error(response: Any, status: int) -> str:
    assert response.status_code == status, response.text
    return response.json()["error"]["code"]


def _skills(profile: dict) -> list[tuple[str, bool, bool]]:
    return [(s["code"], s["listed"], s["verified"]) for s in profile["skills"]]


def _approved_work_on_opportunity_1(conn: pymysql.Connection, contributor_id: int) -> None:
    """An accepted application to opportunity 1 with work Priya approved."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO application (opportunity_id, contributor_id, status, submitted_at, "
            "decided_at) VALUES (1, %s, 'accepted', '2026-10-14 10:00:00', "
            "'2026-10-14 12:00:00')",
            (contributor_id,),
        )
        cur.execute(
            "INSERT INTO work_submission (application_id, description, hours_claimed, "
            "submitted_at) VALUES (%s, 'Typed up 40 recipes.', 6.50, '2026-10-15 10:00:00')",
            (cur.lastrowid,),
        )
        cur.execute(
            "INSERT INTO work_verification (submission_id, verified_by_user_id, decision, "
            "verified_hours, verified_at) VALUES (%s, 2, 'approved', 6.00, "
            "'2026-10-15 15:00:00')",
            (cur.lastrowid,),
        )


# --- reading ------------------------------------------------------------------


def test_get_returns_the_seeded_profile(client: TestClient, contributor: dict[str, str]) -> None:
    profile = _ok(client.get(PROFILE, headers=contributor))

    assert profile["user_id"] == ALEX
    assert (profile["full_name"], profile["email"]) == ("Alex Chen", "alex.chen@grow8.dev")
    assert profile["headline"] == "Software engineering student"
    assert (profile["institution"], profile["city"]) == ("University of Calgary", "Calgary")
    assert profile["has_resume"] is False
    assert profile["updated_at"].endswith("Z")
    # Sorted by name, not code.
    assert _skills(profile) == [
        ("data-cleaning", True, False),
        ("spreadsheets", True, False),
        ("web-basics", True, False),
    ]
    assert [s["name"] for s in profile["skills"]] == [
        "Data cleaning",
        "Spreadsheets",
        "Web basics (HTML/CSS)",
    ]


def test_a_skill_is_verified_by_approved_work_that_required_it(
    client: TestClient, contributor: dict[str, str], seeded_db: pymysql.Connection
) -> None:
    _approved_work_on_opportunity_1(seeded_db, ALEX)

    skills = {s["code"]: s for s in _ok(client.get(PROFILE, headers=contributor))["skills"]}

    def kind(code: str) -> tuple[bool, bool, str | None]:
        return skills[code]["listed"], skills[code]["verified"], skills[code]["verified_at"]

    assert kind("spreadsheets") == (True, True, "2026-10-15T15:00:00Z")
    # Opportunity 1 also required data-entry, which Alex never listed: earned (ADR 0019).
    assert kind("data-entry") == (False, True, "2026-10-15T15:00:00Z")
    # Opportunity 1 didn't require data-cleaning.
    assert kind("data-cleaning") == (True, False, None)
    assert [s["code"] for s in skills.values()] == [
        "data-cleaning",
        "data-entry",
        "spreadsheets",
        "web-basics",
    ]  # sorted by name, earned and listed together


def test_has_resume(
    client: TestClient, contributor: dict[str, str], seeded_db: pymysql.Connection
) -> None:
    with seeded_db.cursor() as cur:
        cur.execute(
            "INSERT INTO contributor_resume (user_id, file_name, content_type, size_bytes, "
            "storage_key, uploaded_at) VALUES (5, 'cv.pdf', 'application/pdf', 10, "
            "'resumes/test', '2026-10-15 10:00:00')"
        )
    assert _ok(client.get(PROFILE, headers=contributor))["has_resume"] is True


# --- PATCH ----------------------------------------------------------------------


def test_patch_changes_only_the_fields_sent(
    client: TestClient, contributor: dict[str, str]
) -> None:
    profile = _ok(
        client.patch(
            PROFILE,
            json={"full_name": "  Alex C. Chen ", "headline": "Data student"},
            headers=contributor,
        )
    )

    assert (profile["full_name"], profile["headline"]) == ("Alex C. Chen", "Data student")
    assert (profile["institution"], profile["city"]) == ("University of Calgary", "Calgary")
    assert len(profile["skills"]) == 3
    assert _ok(client.get(PROFILE, headers=contributor)) == profile
    # The name is the account's: /auth/me shows it too.
    assert _ok(client.get(ME, headers=contributor))["full_name"] == "Alex C. Chen"


def test_patch_clears_optional_fields(client: TestClient, contributor: dict[str, str]) -> None:
    profile = _ok(
        client.patch(
            PROFILE, json={"headline": None, "bio": "", "city": "   "}, headers=contributor
        )
    )
    assert (profile["headline"], profile["bio"], profile["city"]) == (None, None, None)
    assert profile["institution"] == "University of Calgary"


@pytest.mark.parametrize(
    "body",
    [
        {"full_name": None},
        {"full_name": "  "},
        {"email": "alex@example.com"},
        {"skills": ["photography"]},
        {"bio": "x" * 5001},
    ],
)
def test_patch_refuses_bad_input(
    client: TestClient, contributor: dict[str, str], body: dict
) -> None:
    assert _error(client.patch(PROFILE, json=body, headers=contributor), 422) == (
        "VALIDATION_ERROR"
    )
    assert _ok(client.get(PROFILE, headers=contributor))["full_name"] == "Alex Chen"


# --- PUT skills ---------------------------------------------------------------


def test_put_replaces_the_listed_skills(client: TestClient, contributor: dict[str, str]) -> None:
    profile = _ok(
        client.put(
            SKILLS,
            json={"skill_codes": ["translation", "spreadsheets", "translation"]},
            headers=contributor,
        )
    )
    assert _skills(profile) == [("spreadsheets", True, False), ("translation", True, False)]
    assert _skills(_ok(client.get(PROFILE, headers=contributor))) == _skills(profile)


def test_put_keeps_the_skills_it_keeps(
    client: TestClient, contributor: dict[str, str], seeded_db: pymysql.Connection
) -> None:
    def listed_since() -> dict[int, object]:
        with seeded_db.cursor() as cur:
            cur.execute(
                "SELECT skill_id, created_at FROM contributor_skill WHERE contributor_id = 5"
            )
            return dict(cur.fetchall())

    with seeded_db.cursor() as cur:
        cur.execute("UPDATE contributor_skill SET created_at = '2026-01-01 00:00:00'")
    before = listed_since()

    _ok(
        client.put(
            SKILLS, json={"skill_codes": ["spreadsheets", "translation"]}, headers=contributor
        )
    )

    after = listed_since()
    kept = set(before) & set(after)
    assert len(kept) == 1  # spreadsheets
    assert all(after[s] == before[s] for s in kept)


def test_an_empty_list_removes_every_listed_skill(
    client: TestClient, contributor: dict[str, str]
) -> None:
    assert _ok(client.put(SKILLS, json={"skill_codes": []}, headers=contributor))["skills"] == []


def test_unknown_skills_are_listed(client: TestClient, contributor: dict[str, str]) -> None:
    response = client.put(
        SKILLS,
        json={"skill_codes": ["spreadsheets", "underwater-welding", "juggling"]},
        headers=contributor,
    )
    assert _error(response, 422) == "UNKNOWN_SKILL"
    assert response.json()["error"]["details"] == {
        "unknown_skills": ["underwater-welding", "juggling"]
    }
    assert len(_ok(client.get(PROFILE, headers=contributor))["skills"]) == 3


def test_more_than_25_skills_is_a_validation_error(
    client: TestClient, contributor: dict[str, str]
) -> None:
    codes = [f"skill-{i}" for i in range(26)]
    response = client.put(SKILLS, json={"skill_codes": codes}, headers=contributor)
    assert _error(response, 422) == "VALIDATION_ERROR"


def test_editing_skills_never_removes_an_earned_one(
    client: TestClient, contributor: dict[str, str], seeded_db: pymysql.Connection
) -> None:
    """ADR 0019: removing a verified skill removes only the listing; it stays, earned."""
    _approved_work_on_opportunity_1(seeded_db, ALEX)

    removed = _ok(client.put(SKILLS, json={"skill_codes": ["web-basics"]}, headers=contributor))
    assert _skills(removed) == [
        ("data-entry", False, True),
        ("spreadsheets", False, True),
        ("web-basics", True, False),
    ]
    assert _skills(_ok(client.put(SKILLS, json={"skill_codes": []}, headers=contributor))) == [
        ("data-entry", False, True),
        ("spreadsheets", False, True),
    ]

    back = _ok(
        client.put(
            SKILLS, json={"skill_codes": ["web-basics", "spreadsheets"]}, headers=contributor
        )
    )
    spreadsheets = next(s for s in back["skills"] if s["code"] == "spreadsheets")
    assert (spreadsheets["listed"], spreadsheets["verified"]) == (True, True)
    assert spreadsheets["verified_at"] == "2026-10-15T15:00:00Z"


def test_listing_an_earned_skill(
    client: TestClient, contributor: dict[str, str], seeded_db: pymysql.Connection
) -> None:
    _approved_work_on_opportunity_1(seeded_db, ALEX)
    codes = ["data-cleaning", "data-entry", "spreadsheets", "web-basics"]

    profile = _ok(client.put(SKILLS, json={"skill_codes": codes}, headers=contributor))

    assert ("data-entry", True, True) in _skills(profile)
    assert len(profile["skills"]) == 4  # one entry per skill, never two


def test_changing_skills_marks_the_profile_updated(
    client: TestClient, contributor: dict[str, str], seeded_db: pymysql.Connection
) -> None:
    with seeded_db.cursor() as cur:
        cur.execute("UPDATE contributor_profile SET updated_at = '2026-01-01 00:00:00'")

    same = _ok(
        client.put(
            SKILLS,
            json={"skill_codes": ["web-basics", "spreadsheets", "data-cleaning"]},
            headers=contributor,
        )
    )
    assert same["updated_at"] == "2026-01-01T00:00:00Z"  # nothing changed

    changed = _ok(client.put(SKILLS, json={"skill_codes": ["web-basics"]}, headers=contributor))
    assert changed["updated_at"] > "2026-01-01T00:00:00Z"


def test_new_skills_affect_opportunity_matching(
    client: TestClient, contributor: dict[str, str]
) -> None:
    _ok(client.put(SKILLS, json={"skill_codes": ["translation"]}, headers=contributor))

    with get_sessionmaker()() as session:
        matches = find_matching_contributors(session, ["translation"])
        assert [(m.user_id, m.matched_skill_codes) for m in matches] == [(ALEX, ["translation"])]
        assert ALEX not in [
            m.user_id for m in find_matching_contributors(session, ["spreadsheets"])
        ]


def test_matching_uses_listed_skills_only(
    contributor: dict[str, str], seeded_db: pymysql.Connection
) -> None:
    """ADR 0019: an earned skill the contributor hasn't listed doesn't trigger matches;
    they choose what to be notified about by listing it."""
    _approved_work_on_opportunity_1(seeded_db, ALEX)

    with get_sessionmaker()() as session:
        assert ALEX not in [m.user_id for m in find_matching_contributors(session, ["data-entry"])]


# --- a contributor without a profile row --------------------------------------


@pytest.fixture
def without_profile(seeded_db: pymysql.Connection) -> None:
    """Sign-up always creates a profile; seeded or old accounts might not have one."""
    with seeded_db.cursor() as cur:
        cur.execute("DELETE FROM contributor_profile WHERE user_id = 7")


@pytest.mark.usefixtures("without_profile")
def test_a_missing_profile_reads_as_empty(client: TestClient, sam: dict[str, str]) -> None:
    profile = _ok(client.get(PROFILE, headers=sam))
    assert (profile["full_name"], profile["email"]) == ("Sam Patel", "sam.patel@grow8.dev")
    assert [profile[f] for f in ("headline", "bio", "institution", "city")] == [None] * 4
    assert (profile["skills"], profile["updated_at"], profile["has_resume"]) == ([], None, False)


@pytest.mark.usefixtures("without_profile")
def test_the_first_save_creates_the_profile_and_unblocks_applying(
    client: TestClient, sam: dict[str, str]
) -> None:
    refused = client.post(f"{API}/opportunities/8/applications", json={}, headers=sam)
    assert _error(refused, 409) == "CONTRIBUTOR_PROFILE_REQUIRED"
    assert refused.json()["error"]["message"] == "Save your profile first"

    profile = _ok(client.patch(PROFILE, json={"city": "Calgary"}, headers=sam))
    assert profile["city"] == "Calgary"
    assert profile["updated_at"] is not None

    applied = client.post(f"{API}/opportunities/8/applications", json={}, headers=sam)
    assert applied.status_code == 201, applied.text


@pytest.mark.usefixtures("without_profile")
def test_putting_skills_also_creates_the_profile(client: TestClient, sam: dict[str, str]) -> None:
    profile = _ok(client.put(SKILLS, json={"skill_codes": ["photography"]}, headers=sam))
    assert _skills(profile) == [("photography", True, False)]
    assert profile["updated_at"] is not None


# --- who can do what -------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "url", "body"),
    [
        ("GET", PROFILE, None),
        ("PATCH", PROFILE, {"headline": "x"}),
        ("PUT", SKILLS, {"skill_codes": []}),
    ],
)
def test_contributors_only(
    client: TestClient, bakery: dict[str, str], method: str, url: str, body: dict | None
) -> None:
    assert _error(client.request(method, url, json=body, headers=bakery), 403) == "ROLE_FORBIDDEN"
    assert _error(client.request(method, url, json=body), 401) == "AUTH_REQUIRED"


def test_edits_show_on_applications_for_the_creator(
    client: TestClient, contributor: dict[str, str], bakery: dict[str, str]
) -> None:
    applied = client.post(f"{API}/opportunities/1/applications", json={}, headers=contributor)
    assert applied.status_code == 201, applied.text
    _ok(
        client.patch(
            PROFILE, json={"full_name": "Alex C.", "headline": "Data student"}, headers=contributor
        )
    )

    applicant = _ok(
        client.get(f"{API}/applications/{applied.json()['application_id']}", headers=bakery)
    )["applicant"]
    assert (applicant["full_name"], applicant["headline"]) == ("Alex C.", "Data student")
    assert "email" not in applicant


# --- PATCH /auth/me: any role changes their name ------------------------------------


def test_a_creator_changes_their_name(client: TestClient, bakery: dict[str, str]) -> None:
    user = _ok(client.patch(ME, json={"full_name": "  Priya N. "}, headers=bakery))
    assert (user["full_name"], user["role"]) == ("Priya N.", "creator")
    assert _ok(client.get(ME, headers=bakery))["full_name"] == "Priya N."


def test_email_cannot_be_changed(client: TestClient, bakery: dict[str, str]) -> None:
    body = {"full_name": "Priya", "email": "priya@example.com"}
    assert _error(client.patch(ME, json=body, headers=bakery), 422) == "VALIDATION_ERROR"
    assert _ok(client.get(ME, headers=bakery))["email"] == "maple.bakery@grow8.dev"


def test_name_change_needs_a_name_and_a_token(client: TestClient, bakery: dict[str, str]) -> None:
    assert _error(client.patch(ME, json={"full_name": " "}, headers=bakery), 422) == (
        "VALIDATION_ERROR"
    )
    assert _error(client.patch(ME, json={"full_name": "X"}), 401) == "AUTH_REQUIRED"


# --- two first saves at once --------------------------------------------------------


@pytest.fixture
def sessions(seeded_db: pymysql.Connection) -> Iterator[tuple[Session, Session]]:
    factory = get_sessionmaker()
    with factory() as first, factory() as second:
        yield first, second


@pytest.mark.usefixtures("without_profile")
def test_two_first_saves_run_one_after_the_other(sessions: tuple[Session, Session]) -> None:
    """Sam has no profile row. The first save creates and locks it; the second waits for
    that lock (rather than failing on a duplicate key), then applies its own change."""
    first, second = sessions
    sam_1 = user_repository.get_by_id(first, 7)
    sam_2 = user_repository.get_by_id(second, 7)
    assert sam_1 is not None and sam_2 is not None
    profile = user_repository.lock_contributor_profile(first, 7)
    profile.city = "Calgary"

    outcome: list[object] = []

    def save_second() -> None:
        update = ProfileUpdate(headline="Designer")
        outcome.append(contributor_profile_service.update_mine(second, sam_2, update))

    thread = threading.Thread(target=save_second)
    thread.start()
    thread.join(timeout=1)
    assert thread.is_alive(), "the second save should wait for the first's lock"

    first.commit()
    thread.join(timeout=10)

    [saved] = outcome
    assert (saved.city, saved.headline) == ("Calgary", "Designer")  # type: ignore[attr-defined]
