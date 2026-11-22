"""Profile input rules (ADR 0017): trimming, clearing, the name that can't be cleared,
duplicate skills collapsed, and the 25-skill cap."""

import pytest
from pydantic import ValidationError

from app.schemas.auth import UserUpdate
from app.schemas.contributor_profile import MAX_SKILLS, ProfileUpdate, SkillsReplace


def test_only_the_fields_sent_are_set() -> None:
    data = ProfileUpdate.model_validate({"headline": "Designer"})
    assert data.model_fields_set == {"headline"}


def test_whitespace_is_trimmed() -> None:
    data = ProfileUpdate.model_validate({"full_name": "  Alex Chen ", "city": " Calgary  "})
    assert (data.full_name, data.city) == ("Alex Chen", "Calgary")


@pytest.mark.parametrize("cleared", [None, "", "   "])
def test_optional_fields_can_be_cleared(cleared: str | None) -> None:
    fields = ("headline", "bio", "institution", "city")
    data = ProfileUpdate.model_validate(dict.fromkeys(fields, cleared))
    assert data.model_fields_set == set(fields)
    assert all(getattr(data, f) is None for f in fields)


@pytest.mark.parametrize("name", [None, "", "   "])
def test_full_name_cannot_be_cleared(name: str | None) -> None:
    with pytest.raises(ValidationError):
        ProfileUpdate.model_validate({"full_name": name})


@pytest.mark.parametrize(
    ("field", "limit"), [("full_name", 150), ("headline", 150), ("bio", 5000), ("city", 100)]
)
def test_length_limits(field: str, limit: int) -> None:
    assert getattr(ProfileUpdate.model_validate({field: "x" * limit}), field) == "x" * limit
    with pytest.raises(ValidationError):
        ProfileUpdate.model_validate({field: "x" * (limit + 1)})


@pytest.mark.parametrize("body", [{"email": "new@grow8.dev"}, {"skills": ["photography"]}])
def test_unknown_fields_are_refused(body: dict) -> None:
    with pytest.raises(ValidationError):
        ProfileUpdate.model_validate(body)


def test_duplicate_skills_are_collapsed_in_order() -> None:
    data = SkillsReplace.model_validate(
        {"skill_codes": ["photography", " spreadsheets", "photography"]}
    )
    assert data.skill_codes == ["photography", "spreadsheets"]


def test_an_empty_list_is_allowed() -> None:
    assert SkillsReplace.model_validate({"skill_codes": []}).skill_codes == []


def test_at_most_25_different_skills() -> None:
    codes = [f"skill-{i}" for i in range(MAX_SKILLS)]
    assert len(SkillsReplace.model_validate({"skill_codes": codes + codes}).skill_codes) == 25
    with pytest.raises(ValidationError):
        SkillsReplace.model_validate({"skill_codes": [*codes, "one-more"]})


@pytest.mark.parametrize("body", [{}, {"skill_codes": [""]}, {"skill_codes": None}])
def test_skill_codes_are_required_and_non_empty(body: dict) -> None:
    with pytest.raises(ValidationError):
        SkillsReplace.model_validate(body)


def test_name_update_trims_and_refuses_email() -> None:
    assert UserUpdate.model_validate({"full_name": " Priya N. "}).full_name == "Priya N."
    for body in ({"full_name": " "}, {"full_name": "Priya", "email": "p@grow8.dev"}, {}):
        with pytest.raises(ValidationError):
            UserUpdate.model_validate(body)
