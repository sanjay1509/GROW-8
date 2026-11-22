"""A creator's own organization (ADR 0018).

Seeded: Priya Nair (user 2, maple.bakery@grow8.dev) owns Maple Street Bakery
(organization 1), which posts opportunity 1. Every seeded creator has an organization,
so the tests for a creator without one add a new creator account."""

import threading
from collections.abc import Iterator
from typing import Any

import pymysql
import pytest
from fastapi.testclient import TestClient
from grow8_common.db import get_sessionmaker
from grow8_common.models import CreatorOrganization
from sqlalchemy.orm import Session

from app.repositories import user_repository
from app.schemas.organization import OrganizationUpdate
from app.services import organization_service
from tests.conftest import DEV_PASSWORD

API = "/api/v1"
ORG = f"{API}/creators/me/organization"
NEW_CREATOR = "corner.cafe@grow8.dev"


def _ok(response: Any) -> dict:
    assert response.status_code == 200, response.text
    return response.json()


def _error(response: Any, status: int) -> str:
    assert response.status_code == status, response.text
    return response.json()["error"]["code"]


# --- reading and editing -------------------------------------------------------


def test_get_returns_the_seeded_organization(client: TestClient, bakery: dict[str, str]) -> None:
    org = _ok(client.get(ORG, headers=bakery))

    assert (org["organization_id"], org["name"]) == (1, "Maple Street Bakery")
    assert org["organization_type"] == "small_business"
    assert (org["website"], org["city"]) == ("https://example.com/maple-street-bakery", "Calgary")
    assert org["description"].startswith("Family-run neighbourhood bakery.")
    assert org["updated_at"].endswith("Z")
    assert "owner_user_id" not in org


def test_patch_changes_only_the_fields_sent(client: TestClient, bakery: dict[str, str]) -> None:
    org = _ok(
        client.patch(
            ORG,
            json={"name": "  Maple Street Bakery & Café ", "website": "", "city": None},
            headers=bakery,
        )
    )

    assert org["name"] == "Maple Street Bakery & Café"
    assert (org["website"], org["city"]) == (None, None)
    assert org["organization_type"] == "small_business"
    assert org["description"].startswith("Family-run")
    assert _ok(client.get(ORG, headers=bakery)) == org


def test_changing_the_type(client: TestClient, bakery: dict[str, str]) -> None:
    body = {"organization_type": "other"}
    assert _ok(client.patch(ORG, json=body, headers=bakery))["organization_type"] == "other"


@pytest.mark.parametrize(
    "body",
    [
        {"name": None},
        {"name": ""},
        {"organization_type": None},
        {"organization_type": "charity"},
        {"website": "javascript:alert(1)"},
        {"website": "ftp://example.com"},
        {"owner_user_id": 3},
    ],
)
def test_patch_refuses_bad_input(client: TestClient, bakery: dict[str, str], body: dict) -> None:
    assert _error(client.patch(ORG, json=body, headers=bakery), 422) == "VALIDATION_ERROR"
    assert _ok(client.get(ORG, headers=bakery))["name"] == "Maple Street Bakery"


def test_edits_show_on_opportunities(client: TestClient, bakery: dict[str, str]) -> None:
    _ok(client.patch(ORG, json={"name": "Maple Street Café", "city": "Airdrie"}, headers=bakery))

    summary = _ok(client.get(f"{API}/opportunities/1"))["organization"]
    assert (summary["name"], summary["city"]) == ("Maple Street Café", "Airdrie")

    browse = _ok(client.get(f"{API}/opportunities", params={"organization_id": 1}))["items"]
    assert browse and all(o["organization"]["name"] == "Maple Street Café" for o in browse)
    found = _ok(client.get(f"{API}/opportunities", params={"q": "Maple Street Café"}))
    assert found["total"] == len(browse)


# --- who can do what -------------------------------------------------------------


@pytest.mark.parametrize(("method", "body"), [("GET", None), ("PATCH", {"city": "Calgary"})])
def test_creators_only(
    client: TestClient, contributor: dict[str, str], method: str, body: dict | None
) -> None:
    admin = client.post(
        f"{API}/auth/login", json={"email": "admin@grow8.dev", "password": DEV_PASSWORD}
    ).json()["access_token"]
    for headers in (contributor, {"Authorization": f"Bearer {admin}"}):
        response = client.request(method, ORG, json=body, headers=headers)
        assert _error(response, 403) == "ROLE_FORBIDDEN"
    assert _error(client.request(method, ORG, json=body), 401) == "AUTH_REQUIRED"


# --- a creator without an organization --------------------------------------------


@pytest.fixture
def new_creator(client: TestClient, seeded_db: pymysql.Connection) -> dict[str, str]:
    """A creator account with no organization (Wen Li, user id returned by the insert)."""
    with seeded_db.cursor() as cur:
        cur.execute(
            "INSERT INTO user_account (email, password_hash, role, full_name) "
            "SELECT %s, password_hash, 'creator', 'Wen Li' FROM user_account WHERE user_id = 2",
            (NEW_CREATOR,),
        )
    response = client.post(
        f"{API}/auth/login", json={"email": NEW_CREATOR, "password": DEV_PASSWORD}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_no_organization_yet(client: TestClient, new_creator: dict[str, str]) -> None:
    assert _error(client.get(ORG, headers=new_creator), 404) == "ORGANIZATION_NOT_FOUND"
    assert _ok(client.get(f"{API}/opportunities/mine", headers=new_creator))["items"] == []

    draft = {"title": "Help at the café", "description": "Serving.", "category": "community"}
    refused = client.post(f"{API}/opportunities", json=draft, headers=new_creator)
    assert _error(refused, 409) == "ORGANIZATION_REQUIRED"


def test_creating_needs_name_and_type(client: TestClient, new_creator: dict[str, str]) -> None:
    for body in ({"city": "Calgary"}, {"name": "Corner Café"}):
        response = client.patch(ORG, json=body, headers=new_creator)
        assert _error(response, 409) == "ORGANIZATION_REQUIRED"
    assert _error(client.get(ORG, headers=new_creator), 404) == "ORGANIZATION_NOT_FOUND"


def test_the_first_save_creates_it(client: TestClient, new_creator: dict[str, str]) -> None:
    body = {"name": "Corner Café", "organization_type": "small_business", "city": "Calgary"}
    org = _ok(client.patch(ORG, json=body, headers=new_creator))

    assert (org["name"], org["organization_type"], org["city"]) == (
        "Corner Café",
        "small_business",
        "Calgary",
    )
    assert (org["description"], org["website"]) == (None, None)
    assert _ok(client.get(ORG, headers=new_creator)) == org

    draft = {"title": "Help at the café", "description": "Serving.", "category": "community"}
    created = client.post(f"{API}/opportunities", json=draft, headers=new_creator)
    assert created.status_code == 201, created.text
    assert created.json()["organization"]["organization_id"] == org["organization_id"]


# --- two first saves at once --------------------------------------------------------


@pytest.fixture
def sessions(seeded_db: pymysql.Connection) -> Iterator[tuple[Session, Session]]:
    factory = get_sessionmaker()
    with factory() as first, factory() as second:
        yield first, second


@pytest.mark.usefixtures("new_creator")
def test_two_first_saves_run_one_after_the_other(sessions: tuple[Session, Session]) -> None:
    """The new creator has no organization. The first save locks their account and
    creates it; the second waits for that lock (rather than creating a second one and
    failing on uq_creator_organization_owner), then edits the one just created."""
    first, second = sessions
    owner_1 = user_repository.get_by_email(first, NEW_CREATOR)
    owner_2 = user_repository.get_by_email(second, NEW_CREATOR)
    assert owner_1 is not None and owner_2 is not None

    create = OrganizationUpdate(name="Corner Café", organization_type="small_business")
    assert user_repository.lock_organization_of(first, owner_1.user_id) is None
    organization = CreatorOrganization(owner_user_id=owner_1.user_id)
    for field in ("name", "organization_type"):
        setattr(organization, field, getattr(create, field))
    user_repository.add_organization(first, organization)
    first.flush()

    outcome: list[object] = []

    def save_second() -> None:
        both = OrganizationUpdate(name="Corner Café 2", organization_type="other", city="Calgary")
        outcome.append(organization_service.update_mine(second, owner_2, both))

    thread = threading.Thread(target=save_second)
    thread.start()
    thread.join(timeout=1)
    assert thread.is_alive(), "the second save should wait for the first's lock"

    first.commit()
    thread.join(timeout=10)

    [saved] = outcome
    assert saved.organization_id == organization.organization_id  # type: ignore[attr-defined]
    assert (saved.name, saved.city) == ("Corner Café 2", "Calgary")  # type: ignore[attr-defined]
