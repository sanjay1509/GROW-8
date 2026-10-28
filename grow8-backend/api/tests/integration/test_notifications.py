"""Notifications API against the seeded test DB. The consumer services write the rows;
here they are inserted directly. Seeded users: `contributor` fixture is Alex Chen
(user 5), `events_org` is Sofia Martinez (user 4)."""

import pymysql
import pytest
from fastapi.testclient import TestClient

URL = "/api/v1/notifications"
ALEX, SOFIA = 5, 4


def _add(
    conn: pymysql.Connection,
    user_id: int,
    title: str,
    created_at: str,
    read_at: str | None = None,
    notification_type: str = "opportunity_created",
) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO notification (user_id, event_id, notification_type, title, message, "
            "opportunity_id, read_at, created_at) VALUES (%s, UUID(), %s, %s, 'msg', 15, %s, %s)",
            (user_id, notification_type, title, read_at, created_at),
        )
        return cur.lastrowid


@pytest.fixture
def inbox(seeded_db: pymysql.Connection) -> dict[str, int]:
    """Alex: three unread and one read; Sofia: one unread."""
    return {
        "oldest": _add(seeded_db, ALEX, "oldest", "2026-10-10 09:00:00"),
        "read": _add(seeded_db, ALEX, "read", "2026-10-11 09:00:00", "2026-10-11 10:00:00"),
        "middle": _add(seeded_db, ALEX, "middle", "2026-10-12 09:00:00"),
        "newest": _add(seeded_db, ALEX, "newest", "2026-10-13 09:00:00"),
        "sofia": _add(
            seeded_db,
            SOFIA,
            "sofia",
            "2026-10-13 09:00:00",
            notification_type="opportunity_published",
        ),
    }


def _titles(response) -> list[str]:
    assert response.status_code == 200, response.text
    return [n["title"] for n in response.json()["items"]]


# --- auth -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "path"),
    [("get", ""), ("get", "/unread-count"), ("patch", "/1/read"), ("post", "/read-all")],
)
def test_every_endpoint_requires_a_token(client: TestClient, method: str, path: str) -> None:
    response = client.request(method, URL + path)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


# --- listing --------------------------------------------------------------------


def test_lists_only_your_own_notifications_newest_first(
    client: TestClient, contributor: dict[str, str], inbox: dict[str, int]
) -> None:
    response = client.get(URL, headers=contributor)

    assert _titles(response) == ["newest", "middle", "read", "oldest"]
    body = response.json()
    assert (body["total"], body["limit"], body["offset"]) == (4, 20, 0)
    newest = body["items"][0]
    assert newest == {
        "notification_id": inbox["newest"],
        "notification_type": "opportunity_created",
        "title": "newest",
        "message": "msg",
        "opportunity_id": 15,
        "read_at": None,
        "created_at": "2026-10-13T09:00:00Z",
        "is_read": False,
    }
    read = body["items"][2]
    assert (read["is_read"], read["read_at"]) == (True, "2026-10-11T10:00:00Z")


def test_unread_only(
    client: TestClient, contributor: dict[str, str], inbox: dict[str, int]
) -> None:
    response = client.get(URL, params={"unread_only": True}, headers=contributor)
    assert _titles(response) == ["newest", "middle", "oldest"]
    assert response.json()["total"] == 3


def test_pagination(client: TestClient, contributor: dict[str, str], inbox: dict[str, int]) -> None:
    first = client.get(URL, params={"limit": 2, "offset": 0}, headers=contributor)
    second = client.get(URL, params={"limit": 2, "offset": 2}, headers=contributor)
    assert _titles(first) == ["newest", "middle"]
    assert _titles(second) == ["read", "oldest"]
    assert second.json()["total"] == 4


def test_bad_paging_is_rejected(client: TestClient, contributor: dict[str, str]) -> None:
    response = client.get(URL, params={"limit": 0}, headers=contributor)
    assert response.status_code == 422


def test_creators_have_an_inbox_too(
    client: TestClient, events_org: dict[str, str], inbox: dict[str, int]
) -> None:
    response = client.get(URL, headers=events_org)
    assert _titles(response) == ["sofia"]
    assert response.json()["items"][0]["notification_type"] == "opportunity_published"


def test_empty_inbox(client: TestClient, bakery: dict[str, str], inbox: dict[str, int]) -> None:
    response = client.get(URL, headers=bakery)
    assert response.json() == {"items": [], "total": 0, "limit": 20, "offset": 0}
    assert client.get(f"{URL}/unread-count", headers=bakery).json() == {"unread_count": 0}


def test_unread_count(
    client: TestClient, contributor: dict[str, str], inbox: dict[str, int]
) -> None:
    response = client.get(f"{URL}/unread-count", headers=contributor)
    assert response.status_code == 200
    assert response.json() == {"unread_count": 3}


# --- marking read ---------------------------------------------------------------


def test_mark_read_once_and_again(
    client: TestClient, contributor: dict[str, str], inbox: dict[str, int]
) -> None:
    first = client.patch(f"{URL}/{inbox['newest']}/read", headers=contributor)
    assert first.status_code == 200, first.text
    assert first.json()["is_read"] is True
    read_at = first.json()["read_at"]
    assert read_at is not None

    again = client.patch(f"{URL}/{inbox['newest']}/read", headers=contributor)
    assert again.status_code == 200
    assert again.json()["read_at"] == read_at  # idempotent: the first read time is kept
    assert client.get(f"{URL}/unread-count", headers=contributor).json() == {"unread_count": 2}


def test_already_read_notification_keeps_its_read_time(
    client: TestClient, contributor: dict[str, str], inbox: dict[str, int]
) -> None:
    response = client.patch(f"{URL}/{inbox['read']}/read", headers=contributor)
    assert response.json()["read_at"] == "2026-10-11T10:00:00Z"


@pytest.mark.parametrize("which", ["sofia", "missing"])
def test_someone_elses_or_missing_notification_is_not_found(
    client: TestClient, contributor: dict[str, str], inbox: dict[str, int], which: str
) -> None:
    notification_id = inbox.get(which, 999_999)
    response = client.patch(f"{URL}/{notification_id}/read", headers=contributor)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOTIFICATION_NOT_FOUND"


def test_cannot_mark_someone_elses_notification_read(
    client: TestClient,
    contributor: dict[str, str],
    events_org: dict[str, str],
    inbox: dict[str, int],
) -> None:
    client.patch(f"{URL}/{inbox['sofia']}/read", headers=contributor)
    assert client.get(f"{URL}/unread-count", headers=events_org).json() == {"unread_count": 1}


def test_read_all_marks_only_your_own(
    client: TestClient,
    contributor: dict[str, str],
    events_org: dict[str, str],
    inbox: dict[str, int],
) -> None:
    response = client.post(f"{URL}/read-all", headers=contributor)
    assert response.status_code == 200
    assert response.json() == {"marked_read": 3}

    assert client.get(f"{URL}/unread-count", headers=contributor).json() == {"unread_count": 0}
    assert client.get(f"{URL}/unread-count", headers=events_org).json() == {"unread_count": 1}
    listed = client.get(URL, headers=contributor).json()["items"]
    assert next(n for n in listed if n["title"] == "read")["read_at"] == "2026-10-11T10:00:00Z"

    assert client.post(f"{URL}/read-all", headers=contributor).json() == {"marked_read": 0}
