"""Recognise the MySQL errors that mean "a rule was broken", so services can turn
them into domain errors instead of a 500.

Triggers in db/init/001_schema.sql raise SQLSTATE 45000 (MySQL error 1644) with a
message that starts with the rule name, e.g. "applicant_limit_reached: ...".
"""

from sqlalchemy.exc import DBAPIError

TRIGGER_ERROR = 1644
DUPLICATE_KEY = 1062


def _code_and_message(exc: DBAPIError) -> tuple[int | None, str]:
    args = getattr(exc.orig, "args", ())
    code = args[0] if args and isinstance(args[0], int) else None
    message = str(args[1]) if len(args) > 1 else ""
    return code, message


def trigger_rule(exc: DBAPIError) -> str | None:
    """The rule name a trigger rejected the write with, or None for any other error."""
    code, message = _code_and_message(exc)
    if code != TRIGGER_ERROR:
        return None
    return message.split(":", 1)[0].strip() or None


def duplicate_key(exc: DBAPIError, key_name: str) -> bool:
    """True if the write broke the UNIQUE key `key_name`."""
    code, message = _code_and_message(exc)
    return code == DUPLICATE_KEY and key_name in message
