import pymysql
from sqlalchemy.exc import IntegrityError, OperationalError

from app.repositories.db_errors import duplicate_key, trigger_rule


def _operational(code: int, message: str) -> OperationalError:
    return OperationalError("INSERT ...", {}, pymysql.err.OperationalError(code, message))


def test_trigger_rule_is_the_text_before_the_colon() -> None:
    exc = _operational(1644, "applicant_limit_reached: opportunity has no places left")

    assert trigger_rule(exc) == "applicant_limit_reached"


def test_other_errors_are_not_trigger_rules() -> None:
    assert trigger_rule(_operational(2013, "Lost connection to MySQL server")) is None


def test_duplicate_key_matches_only_the_named_key() -> None:
    exc = IntegrityError(
        "INSERT ...",
        {},
        pymysql.err.IntegrityError(
            1062,
            "Duplicate entry '5-1' for key 'application.uq_application_contributor_opportunity'",
        ),
    )

    assert duplicate_key(exc, "uq_application_contributor_opportunity")
    assert not duplicate_key(exc, "uq_feedback_application_author")
