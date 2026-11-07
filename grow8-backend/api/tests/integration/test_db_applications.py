"""Applying to an opportunity: open status, deadline and applicant limit (decision 4).

These rules live in trg_application_bi / trg_application_bu, so they hold for every
code path that writes an application. The limit counts active applications
(pending + accepted); rejected and withdrawn ones free their place.

Seeded opportunities used here (all owned by organization 1 unless noted):
  1  open, limit 2, deadline 2026-11-20
  2  open, limit 1, deadline 2026-11-05
  10 open, limit 6, deadline 2026-10-10 (organization 2)
  11 closed (organization 2)
"""

import threading

import pymysql
import pytest
from grow8_common.config import get_settings

TRIGGER_ERROR = 1644
BEFORE_DEADLINE = "2026-10-15 10:00:00"


def _execute(conn: pymysql.Connection, sql: str, *args: object) -> int:
    with conn.cursor() as cur:
        cur.execute(sql, args or None)
        return cur.lastrowid


def apply(
    conn: pymysql.Connection,
    opportunity_id: int,
    contributor_id: int,
    submitted_at: str = BEFORE_DEADLINE,
    status: str = "pending",
) -> int:
    decided = None if status in ("pending", "withdrawn") else "2026-10-20 12:00:00"
    return _execute(
        conn,
        "INSERT INTO application (opportunity_id, contributor_id, status, submitted_at, "
        "decided_at) VALUES (%s, %s, %s, %s, %s)",
        opportunity_id,
        contributor_id,
        status,
        submitted_at,
        decided,
    )


def refused_with(rule: str, action, *args) -> None:
    with pytest.raises(pymysql.MySQLError) as exc_info:
        action(*args)
    code, message = exc_info.value.args
    assert code == TRIGGER_ERROR, message
    assert message.startswith(rule), message


def test_applications_fill_up_to_the_limit_and_no_further(seeded_db: pymysql.Connection) -> None:
    apply(seeded_db, 1, 5)
    apply(seeded_db, 1, 6)
    refused_with("applicant_limit_reached", apply, seeded_db, 1, 7)


def test_rejected_and_withdrawn_applications_free_their_place(
    seeded_db: pymysql.Connection,
) -> None:
    first = apply(seeded_db, 2, 5)
    refused_with("applicant_limit_reached", apply, seeded_db, 2, 6)

    _execute(
        seeded_db,
        "UPDATE application SET status = 'rejected', decided_at = '2026-10-20 12:00:00' "
        "WHERE application_id = %s",
        first,
    )
    second = apply(seeded_db, 2, 6)

    # the rejected one cannot come back while the place is taken
    refused_with(
        "applicant_limit_reached",
        _execute,
        seeded_db,
        "UPDATE application SET status = 'accepted' WHERE application_id = %s",
        first,
    )
    _execute(
        seeded_db, "UPDATE application SET status = 'withdrawn' WHERE application_id = %s", second
    )
    _execute(
        seeded_db, "UPDATE application SET status = 'accepted' WHERE application_id = %s", first
    )


def test_cannot_apply_after_the_deadline(seeded_db: pymysql.Connection) -> None:
    refused_with("application_deadline_passed", apply, seeded_db, 10, 5, "2026-10-11 00:00:00")
    apply(seeded_db, 10, 5, "2026-10-10 23:59:59")  # the deadline itself is still on time


def test_cannot_apply_to_an_opportunity_that_is_not_open(seeded_db: pymysql.Connection) -> None:
    refused_with("application_closed", apply, seeded_db, 11, 5, "2026-07-15 10:00:00")
    refused_with("application_closed", apply, seeded_db, 14, 5)  # draft


def test_inactive_applications_skip_the_capacity_check(seeded_db: pymysql.Connection) -> None:
    apply(seeded_db, 2, 5)
    # a withdrawn row takes no place, so it is accepted even though the limit is reached
    apply(seeded_db, 2, 6, status="withdrawn")


def test_application_cannot_move_or_be_backdated_later(seeded_db: pymysql.Connection) -> None:
    app_id = apply(seeded_db, 1, 5)
    for change in (
        "opportunity_id = 4",
        "contributor_id = 6",
        "submitted_at = '2026-10-01 00:00:00'",
    ):
        refused_with(
            "application_immutable",
            _execute,
            seeded_db,
            f"UPDATE application SET {change} WHERE application_id = %s",
            app_id,
        )


def test_application_cannot_be_dated_in_the_future(seeded_db: pymysql.Connection) -> None:
    refused_with("application_future_dated", apply, seeded_db, 4, 5, "2099-01-01 00:00:00")


def test_two_people_racing_for_the_last_place_cannot_both_get_it(
    seeded_db: pymysql.Connection,
) -> None:
    """Opportunity 2 has one place. Two transactions apply at the same moment: the
    second waits on the opportunity row lock and is refused once the first commits."""
    s = get_settings()

    def connect() -> pymysql.Connection:
        return pymysql.connect(
            host=s.mysql_host,
            port=s.mysql_port,
            user=s.mysql_user,
            password=s.mysql_password,
            database=s.mysql_database,
            autocommit=False,
        )

    first, second = connect(), connect()
    outcome: dict[str, object] = {}
    try:
        first.begin()
        apply(first, 2, 5)  # holds the lock on opportunity 2, not yet committed

        def second_applicant() -> None:
            try:
                second.begin()
                apply(second, 2, 6)
                second.commit()
                outcome["second"] = "accepted"
            except pymysql.MySQLError as exc:
                second.rollback()
                outcome["second"] = exc.args

        racer = threading.Thread(target=second_applicant)
        racer.start()
        racer.join(timeout=1.0)
        assert racer.is_alive(), "second applicant should be waiting on the row lock"

        first.commit()
        racer.join(timeout=30)
        assert not racer.is_alive()
    finally:
        first.close()
        second.close()

    code, message = outcome["second"]
    assert code == TRIGGER_ERROR
    assert message.startswith("applicant_limit_reached")
    with seeded_db.cursor() as cur:
        cur.execute(
            "SELECT contributor_id FROM application WHERE opportunity_id = 2 "
            "AND status IN ('pending', 'accepted')"
        )
        assert cur.fetchall() == ((5,),)
