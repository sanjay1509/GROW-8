"""Database-level business rules from docs/db/relationship-validation.md (I1-I9).

Each rule is tested both ways: a valid row is accepted and an invalid one is refused
by MySQL itself, whichever code path writes it. Trigger violations raise error 1644
(SQLSTATE 45000) with a message that starts with the rule name.

Seeded data used here: admin 1; creators 2, 3, 4 owning organizations 1, 2, 3;
contributors 5, 6, 7; opportunity 1 is open and belongs to organization 1 (creator 2);
badge 1 exists.
"""

from collections.abc import Callable

import pymysql
import pytest

TRIGGER_ERROR = 1644
FK_ERROR = 1452

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
    """Assert the statement is refused with `error_code`; return MySQL's message."""
    with pytest.raises(pymysql.MySQLError) as exc_info:
        db(sql, *args)
    code, message = exc_info.value.args[0], exc_info.value.args[1]
    assert code == error_code, message
    return message


def application(db: Exec, contributor_id: int = 5, status: str = "accepted") -> int:
    """Application to opportunity 1 (Maple Street Bakery, owner 2)."""
    decided = None if status == "pending" else "2026-10-20 12:00:00"
    return db(
        "INSERT INTO application (opportunity_id, contributor_id, status, decided_at) "
        "VALUES (1, %s, %s, %s)",
        contributor_id,
        status,
        decided,
    )


def submission(db: Exec, application_id: int, hours: str = "5.00") -> int:
    return db(
        "INSERT INTO work_submission (application_id, description, hours_claimed) "
        "VALUES (%s, 'Done', %s)",
        application_id,
        hours,
    )


def verification(db: Exec, submission_id: int, decision: str = "approved", by: int = 2) -> int:
    hours = "5.00" if decision == "approved" else None
    return db(
        "INSERT INTO work_verification (submission_id, verified_by_user_id, decision, "
        "verified_hours) VALUES (%s, %s, %s, %s)",
        submission_id,
        by,
        decision,
        hours,
    )


def feedback(db: Exec, application_id: int, author: int, subject: int, rating: int = 4) -> int:
    return db(
        "INSERT INTO feedback (application_id, author_user_id, subject_user_id, rating) "
        "VALUES (%s, %s, %s, %s)",
        application_id,
        author,
        subject,
        rating,
    )


def query(seeded_db: pymysql.Connection, sql: str, *args: object) -> list[tuple]:
    with seeded_db.cursor() as cur:
        cur.execute(sql, args or None)
        return list(cur.fetchall())


# --- I6: role rules ------------------------------------------------------------


def test_contributor_profile_requires_contributor_role(db: Exec) -> None:
    message = refused(db, TRIGGER_ERROR, "INSERT INTO contributor_profile (user_id) VALUES (2)")
    assert message.startswith("contributor_profile_role")

    new_user = db(
        "INSERT INTO user_account (email, password_hash, role, full_name) "
        "VALUES ('new@grow8.dev', 'x', 'contributor', 'New Contributor')"
    )
    db("INSERT INTO contributor_profile (user_id) VALUES (%s)", new_user)


def test_organization_owner_requires_creator_role(db: Exec) -> None:
    message = refused(
        db,
        TRIGGER_ERROR,
        "INSERT INTO creator_organization (owner_user_id, name, organization_type) "
        "VALUES (5, 'Not a creator', 'other')",
    )
    assert message.startswith("organization_owner_role")

    creator = db(
        "INSERT INTO user_account (email, password_hash, role, full_name) "
        "VALUES ('shop@grow8.dev', 'x', 'creator', 'New Creator')"
    )
    db(
        "INSERT INTO creator_organization (owner_user_id, name, organization_type) "
        "VALUES (%s, 'Corner Shop', 'small_business')",
        creator,
    )


def test_admin_review_requires_admin_role(db: Exec) -> None:
    fb = feedback(db, application(db), author=5, subject=2)
    message = refused(
        db,
        TRIGGER_ERROR,
        "INSERT INTO admin_review (feedback_id, admin_user_id, decision) "
        "VALUES (%s, 2, 'approved')",
        fb,
    )
    assert message.startswith("reviewer_role")
    db(
        "INSERT INTO admin_review (feedback_id, admin_user_id, decision) "
        "VALUES (%s, 1, 'approved')",
        fb,
    )


def test_role_cannot_change_once_rows_depend_on_it(db: Exec) -> None:
    message = refused(
        db, TRIGGER_ERROR, "UPDATE user_account SET role = 'creator' WHERE user_id = 5"
    )
    assert message.startswith("role_locked")

    # Other updates to the same account are unaffected.
    db("UPDATE user_account SET full_name = 'Alex C.' WHERE user_id = 5")
    # An account with nothing attached can still change role.
    spare = db(
        "INSERT INTO user_account (email, password_hash, role, full_name) "
        "VALUES ('spare@grow8.dev', 'x', 'contributor', 'Spare')"
    )
    db("UPDATE user_account SET role = 'creator' WHERE user_id = %s", spare)


def test_only_the_organization_owner_verifies_work(db: Exec) -> None:
    sub = submission(db, application(db))
    message = refused(
        db,
        TRIGGER_ERROR,
        "INSERT INTO work_verification (submission_id, verified_by_user_id, decision, "
        "verified_hours) VALUES (%s, 3, 'approved', 5)",
        sub,
    )
    assert message.startswith("verifier_not_owner")
    verification(db, sub, by=2)


# --- I7: workflow rules --------------------------------------------------------


def test_work_needs_an_accepted_application(db: Exec) -> None:
    message = refused(
        db,
        TRIGGER_ERROR,
        "INSERT INTO work_submission (application_id, description, hours_claimed) "
        "VALUES (%s, 'Done', 5)",
        application(db, status="pending"),
    )
    assert message.startswith("submission_requires_accepted")
    submission(db, application(db, contributor_id=6, status="accepted"))


def test_accepted_application_with_work_cannot_be_withdrawn(db: Exec) -> None:
    app_id = application(db)
    db("UPDATE application SET status = 'withdrawn' WHERE application_id = %s", app_id)
    db("UPDATE application SET status = 'accepted' WHERE application_id = %s", app_id)
    submission(db, app_id)
    message = refused(
        db,
        TRIGGER_ERROR,
        "UPDATE application SET status = 'withdrawn' WHERE application_id = %s",
        app_id,
    )
    assert message.startswith("submission_requires_accepted")


def test_verification_points_need_an_approved_verification_of_the_same_contributor(
    db: Exec,
) -> None:
    rejected = verification(db, submission(db, application(db, contributor_id=5)), "rejected")
    approved = verification(db, submission(db, application(db, contributor_id=6)), "approved")
    insert = (
        "INSERT INTO point_transaction (contributor_id, points, source, verification_id) "
        "VALUES (%s, 10, 'work_verified', %s)"
    )

    assert refused(db, TRIGGER_ERROR, insert, 5, rejected).startswith("points_require_approval")
    assert refused(db, TRIGGER_ERROR, insert, 5, approved).startswith("points_wrong_contributor")
    db(insert, 6, approved)


def test_badge_points_only_for_an_earned_badge(db: Exec) -> None:
    insert = (
        "INSERT INTO point_transaction (contributor_id, points, source, badge_id) "
        "VALUES (6, 50, 'badge_awarded', 1)"
    )
    refused(db, FK_ERROR, insert)
    db("INSERT INTO contributor_badge (contributor_id, badge_id) VALUES (6, 1)")
    db(insert)


# --- I2: feedback participants -------------------------------------------------


def test_feedback_only_between_the_people_on_the_application(db: Exec) -> None:
    app_id = application(db, contributor_id=5)  # contributor 5 <-> creator 2

    assert refused(
        db,
        TRIGGER_ERROR,
        "INSERT INTO feedback (application_id, author_user_id, subject_user_id, rating) "
        "VALUES (%s, 6, 2, 1)",
        app_id,
    ).startswith("feedback_participants")
    assert refused(
        db,
        TRIGGER_ERROR,
        "INSERT INTO feedback (application_id, author_user_id, subject_user_id, rating) "
        "VALUES (%s, 5, 3, 1)",
        app_id,
    ).startswith("feedback_participants")

    feedback(db, app_id, author=5, subject=2)  # contributor rates creator
    feedback(db, app_id, author=2, subject=5)  # creator rates contributor

