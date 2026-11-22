"""Database-level rules for opportunity reports (ADR 0016; R24–R27 in
docs/db/relationship-validation.md).

Each rule is tested both ways, as in test_db_integrity.py: a valid row is accepted and
an invalid one is refused by MySQL itself. Seeded data: admin 1; creators 2 and 3;
contributors 5, 6, 7; opportunities 1 and 4 are open, 15 is a draft.
"""

from collections.abc import Callable

import pymysql
import pytest

TRIGGER_ERROR = 1644
DUPLICATE_KEY = 1062
CHECK_VIOLATED = 3819

Exec = Callable[..., int]


@pytest.fixture
def db(seeded_db: pymysql.Connection) -> Exec:
    """Run one statement on the seeded test database; returns lastrowid."""

    def run(sql: str, *args: object) -> int:
        with seeded_db.cursor() as cur:
            cur.execute(sql, args or None)
            return cur.lastrowid

    return run


def refused(db: Exec, error_code: int, sql: str, *args: object) -> str:
    with pytest.raises(pymysql.MySQLError) as exc_info:
        db(sql, *args)
    code, message = exc_info.value.args[0], exc_info.value.args[1]
    assert code == error_code, message
    return message


REPORT = (
    "INSERT INTO opportunity_report (opportunity_id, reporter_user_id, reason) "
    "VALUES (%s, %s, 'misleading_terms')"
)
REVIEW = (
    "INSERT INTO report_review (report_id, admin_user_id, decision, reason) VALUES (%s, %s, %s, %s)"
)


@pytest.mark.parametrize("user_id", [1, 3])  # an admin, a creator
def test_only_contributors_report(db: Exec, user_id: int) -> None:
    message = refused(db, TRIGGER_ERROR, REPORT, 1, user_id)
    assert message.startswith("reporter_role")
    db(REPORT, 1, 5)


def test_only_published_opportunities_can_be_reported(db: Exec) -> None:
    message = refused(db, TRIGGER_ERROR, REPORT, 15, 5)  # draft
    assert message.startswith("report_requires_published")

    db("UPDATE opportunity SET status = 'cancelled' WHERE opportunity_id = 4")
    message = refused(db, TRIGGER_ERROR, REPORT, 4, 5)
    assert message.startswith("report_requires_published")

    db("UPDATE opportunity SET status = 'closed' WHERE opportunity_id = 1")
    db(REPORT, 1, 5)  # closed is still published


def test_one_report_per_contributor_per_opportunity(db: Exec) -> None:
    db(REPORT, 1, 5)
    message = refused(db, DUPLICATE_KEY, REPORT, 1, 5)
    assert "uq_opportunity_report_reporter" in message
    db(REPORT, 1, 6)  # another contributor
    db(REPORT, 4, 5)  # another opportunity


def test_only_admins_review_reports(db: Exec) -> None:
    report = db(REPORT, 1, 5)
    message = refused(db, TRIGGER_ERROR, REVIEW, report, 2, "dismissed", None)
    assert message.startswith("report_reviewer_role")
    db(REVIEW, report, 1, "dismissed", None)


def test_each_report_is_reviewed_once(db: Exec) -> None:
    report = db(REPORT, 1, 5)
    db(REVIEW, report, 1, "dismissed", None)
    message = refused(db, DUPLICATE_KEY, REVIEW, report, 1, "upheld", "Misleading pay.")
    assert "uq_report_review_report" in message


def test_a_takedown_always_has_a_reason(db: Exec) -> None:
    report = db(REPORT, 1, 5)
    message = refused(db, CHECK_VIOLATED, REVIEW, report, 1, "upheld", None)
    assert "chk_report_review_reason" in message
    db(REVIEW, report, 1, "upheld", "The pay is not what was advertised.")


def test_reporting_or_reviewing_locks_the_role(db: Exec) -> None:
    contributor = db(
        "INSERT INTO user_account (email, password_hash, role, full_name) "
        "VALUES ('reporter@grow8.dev', 'x', 'contributor', 'Reporter')"
    )
    admin = db(
        "INSERT INTO user_account (email, password_hash, role, full_name) "
        "VALUES ('reviewer@grow8.dev', 'x', 'admin', 'Reviewer')"
    )
    report = db(REPORT, 1, contributor)
    db(REVIEW, report, admin, "dismissed", None)

    for user_id in (contributor, admin):
        message = refused(
            db,
            TRIGGER_ERROR,
            "UPDATE user_account SET role = 'creator' WHERE user_id = %s",
            user_id,
        )
        assert message.startswith("role_locked")
