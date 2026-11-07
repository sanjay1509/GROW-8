"""The workflow seed (004_seed_workflow.sql) and the ENSF 608 database questions
(db/queries/database_questions.sql).

The seed must load cleanly on top of 002 with every integrity trigger active, and
each of the eight queries must return the answer documented in
docs/db/database-questions.md.
"""

import re
from decimal import Decimal

import pymysql
import pytest
from conftest import DB_INIT_DIR

QUERIES_FILE = DB_INIT_DIR.parent / "queries" / "database_questions.sql"


def _run_script(conn: pymysql.Connection, sql: str) -> None:
    with conn.cursor() as cur:
        cur.execute(sql)
        while cur.nextset():
            pass


def _rows(conn: pymysql.Connection, sql: str) -> list[tuple]:
    with conn.cursor() as cur:
        cur.execute(sql)
        return list(cur.fetchall())


@pytest.fixture
def workflow_db(seeded_db: pymysql.Connection) -> pymysql.Connection:
    _run_script(seeded_db, (DB_INIT_DIR / "004_seed_workflow.sql").read_text(encoding="utf-8"))
    return seeded_db


@pytest.fixture
def questions(workflow_db: pymysql.Connection) -> dict[int, str]:
    """Q number -> SELECT statement; the SET parameters are applied to the session."""
    script = QUERIES_FILE.read_text(encoding="utf-8")
    parts = re.split(r"^-- Q(\d+):", script, flags=re.MULTILINE)
    _run_script(workflow_db, parts[0])  # header: SET @as_of, @category, ...
    return {
        int(number): f"-- Q{number}:{body}"
        for number, body in zip(parts[1::2], parts[2::2], strict=True)
    }


def test_seed_loads_and_closed_opportunity_stays_closed(workflow_db: pymysql.Connection) -> None:
    counts = dict(
        _rows(
            workflow_db,
            "SELECT 'application', COUNT(*) FROM application UNION ALL "
            "SELECT 'work_submission', COUNT(*) FROM work_submission UNION ALL "
            "SELECT 'work_verification', COUNT(*) FROM work_verification UNION ALL "
            "SELECT 'feedback', COUNT(*) FROM feedback UNION ALL "
            "SELECT 'admin_review', COUNT(*) FROM admin_review UNION ALL "
            "SELECT 'point_transaction', COUNT(*) FROM point_transaction",
        )
    )
    assert counts == {
        "application": 14,
        "work_submission": 5,
        "work_verification": 4,
        "feedback": 7,
        "admin_review": 5,
        "point_transaction": 8,
    }
    assert _rows(workflow_db, "SELECT status FROM opportunity WHERE opportunity_id = 11") == [
        ("closed",)
    ]


def test_views_return_the_seeded_history(workflow_db: pymysql.Connection) -> None:
    assert _rows(
        workflow_db,
        "SELECT contributor_id, total_points, leaderboard_rank FROM v_leaderboard "
        "ORDER BY leaderboard_rank",
    ) == [(6, Decimal(195), 1), (5, Decimal(80), 2), (7, Decimal(0), 3)]
    assert _rows(
        workflow_db,
        "SELECT contributor_id, skill_id FROM v_contributor_skill WHERE is_verified "
        "ORDER BY contributor_id, skill_id",
    ) == [(6, 7), (6, 9)]


def test_seeded_full_opportunity_refuses_another_applicant(
    workflow_db: pymysql.Connection,
) -> None:
    # opportunity 1 has two places and two pending applications in the seed
    with pytest.raises(pymysql.MySQLError) as exc_info:
        _run_script(
            workflow_db,
            "INSERT INTO application (opportunity_id, contributor_id, submitted_at) "
            "VALUES (1, 5, '2026-11-04 10:00:00')",
        )
    assert exc_info.value.args[1].startswith("applicant_limit_reached")


def test_q1_open_community_opportunities(
    workflow_db: pymysql.Connection, questions: dict[int, str]
) -> None:
    rows = _rows(workflow_db, questions[1])
    assert [r[0] for r in rows] == [12, 5, 4, 8, 13]  # ordered by deadline


def test_q2_applicants_and_places(
    workflow_db: pymysql.Connection, questions: dict[int, str]
) -> None:
    rows = _rows(workflow_db, questions[2])
    assert len(rows) == 14
    places = {(r[0], int(r[5]), r[6]) for r in rows}
    assert (1, 2, 2) in places  # opportunity 1 is full
    assert (2, 1, 1) in places  # rejected applicant does not take the place


def test_q3_submissions_awaiting_verification(
    workflow_db: pymysql.Connection, questions: dict[int, str]
) -> None:
    rows = _rows(workflow_db, questions[3])
    assert [(r[0], r[2], r[6]) for r in rows] == [(5, "Alex Chen", "Daniel Okafor")]


def test_q4_verified_hours(workflow_db: pymysql.Connection, questions: dict[int, str]) -> None:
    rows = _rows(workflow_db, questions[4])
    assert [(r[0], r[2], r[3]) for r in rows] == [
        (6, Decimal("14.00"), 2),
        (5, Decimal("5.00"), 1),
        (7, Decimal("0.00"), 0),
    ]


def test_q5_leaderboard_for_october(
    workflow_db: pymysql.Connection, questions: dict[int, str]
) -> None:
    rows = _rows(workflow_db, questions[5])
    assert [(r[0], r[2], r[3]) for r in rows] == [(6, Decimal(105), 1)]


def test_q6_badges_by_popularity(
    workflow_db: pymysql.Connection, questions: dict[int, str]
) -> None:
    rows = _rows(workflow_db, questions[6])
    assert [(r[0], r[3]) for r in rows] == [(1, 2), (4, 2), (2, 1), (3, 0)]


def test_q7_open_discrepancy_reports(
    workflow_db: pymysql.Connection, questions: dict[int, str]
) -> None:
    rows = _rows(workflow_db, questions[7])
    # feedback 7 also reports a discrepancy but was already reviewed
    assert [(r[0], r[1], r[3]) for r in rows] == [(5, 10, "Sam Patel")]


def test_q8_creator_rating_from_approved_feedback_only(
    workflow_db: pymysql.Connection, questions: dict[int, str]
) -> None:
    rows = _rows(workflow_db, questions[8])
    assert [(r[0], r[3], r[4]) for r in rows] == [(3, Decimal("4.50"), 2)]
