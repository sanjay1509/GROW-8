"""Test setup.

Integration tests run against a separate `grow8_test` database (created by
db/init/003_test_database.sh), so they never touch the shared dev data.
The schema is loaded once per session and the seed is re-applied before each test.
"""

import os
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

# Must happen before any app/grow8_common import reads (and caches) settings.
os.environ["MYSQL_DATABASE"] = "grow8_test"

import pymysql  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from grow8_common.config import get_settings  # noqa: E402
from pymysql.constants import CLIENT  # noqa: E402

from app.events.publisher import get_publisher  # noqa: E402
from app.main import app  # noqa: E402
from tests.fakes import FakePublisher  # noqa: E402

DB_INIT_DIR = Path(os.environ.get("GROW8_DB_INIT_DIR", "/app/db/init"))
DEV_PASSWORD = "Grow8Dev!2026"
# Seeded deadlines are fixed dates, so tests pin "now" instead of using the real clock.
FROZEN_NOW = datetime(2026, 10, 16, 12, 0, 0)


def _connect() -> pymysql.Connection:
    s = get_settings()
    return pymysql.connect(
        host=s.mysql_host,
        port=s.mysql_port,
        user=s.mysql_user,
        password=s.mysql_password,
        database=s.mysql_database,
        client_flag=CLIENT.MULTI_STATEMENTS,
        autocommit=True,
    )


def _run_sql_file(conn: pymysql.Connection, path: Path) -> None:
    with conn.cursor() as cur:
        cur.execute(path.read_text(encoding="utf-8"))
        while cur.nextset():
            pass


def _tables(conn: pymysql.Connection) -> list[str]:
    with conn.cursor() as cur:
        cur.execute("SHOW TABLES")
        return [row[0] for row in cur.fetchall()]


def _clear_tables(conn: pymysql.Connection, drop: bool) -> None:
    statement = "DROP TABLE `{}`" if drop else "DELETE FROM `{}`"
    with conn.cursor() as cur:
        cur.execute("SET FOREIGN_KEY_CHECKS = 0")
        for table in _tables(conn):
            cur.execute(statement.format(table))
        cur.execute("SET FOREIGN_KEY_CHECKS = 1")


@pytest.fixture(scope="session")
def test_db() -> Iterator[pymysql.Connection]:
    if not (DB_INIT_DIR / "001_schema.sql").exists():
        pytest.skip(f"{DB_INIT_DIR} not mounted; run tests via `make test`")
    conn = _connect()
    _clear_tables(conn, drop=True)
    _run_sql_file(conn, DB_INIT_DIR / "001_schema.sql")
    yield conn
    conn.close()


@pytest.fixture
def seeded_db(test_db: pymysql.Connection) -> pymysql.Connection:
    """Fresh copy of the seed data for every test."""
    _clear_tables(test_db, drop=False)
    _run_sql_file(test_db, DB_INIT_DIR / "002_seed.sql")
    return test_db


@pytest.fixture
def publisher() -> Iterator[FakePublisher]:
    fake = FakePublisher()
    app.dependency_overrides[get_publisher] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_publisher, None)


@pytest.fixture
def client(
    seeded_db: pymysql.Connection, publisher: FakePublisher, monkeypatch: pytest.MonkeyPatch
) -> TestClient:
    monkeypatch.setattr("app.services.opportunity_service.utcnow", lambda: FROZEN_NOW)
    return TestClient(app)


def _login(client: TestClient, email: str) -> dict[str, str]:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": DEV_PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture
def bakery(client: TestClient) -> dict[str, str]:
    """Creator who owns Maple Street Bakery (organization 1)."""
    return _login(client, "maple.bakery@grow8.dev")


@pytest.fixture
def events_org(client: TestClient) -> dict[str, str]:
    """Creator who owns YYC Neighbourhood Events (organization 3)."""
    return _login(client, "yyc.events@grow8.dev")


@pytest.fixture
def contributor(client: TestClient) -> dict[str, str]:
    return _login(client, "alex.chen@grow8.dev")
