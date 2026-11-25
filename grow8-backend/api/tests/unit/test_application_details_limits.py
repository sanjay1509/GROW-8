"""Limits on application_details (#49): at most 20 entries, keys of 1-50 characters,
values of at most 2000. The apply form sends six short answers."""

import pytest
from pydantic import ValidationError

from app.schemas.application import MAX_DETAILS, ApplicationCreate

FORM = {
    "name": "Alex Chen",
    "email": "alex.chen@grow8.dev",
    "phone": "403-555-0101",
    "study": "Software engineering",
    "experience": "x" * 2000,
    "achievements": "Dean's list",
}


def test_the_apply_form_fits() -> None:
    assert ApplicationCreate(application_details=FORM).application_details == FORM


def test_at_most_20_entries() -> None:
    entries = {f"q{i}": "a" for i in range(MAX_DETAILS)}
    assert len(ApplicationCreate(application_details=entries).application_details) == 20
    with pytest.raises(ValidationError):
        ApplicationCreate(application_details={**entries, "one-more": "a"})


@pytest.mark.parametrize(
    "details",
    [{"": "a"}, {"k" * 51: "a"}, {"experience": "x" * 2001}, {"years": 3}, {"tags": ["a"]}],
)
def test_bad_entries_are_refused(details: dict) -> None:
    with pytest.raises(ValidationError):
        ApplicationCreate(application_details=details)
