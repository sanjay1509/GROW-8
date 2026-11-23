"""The signed-in contributor's own profile and listed skills (ADR 0017)."""

from typing import Annotated, Self

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.common import UtcDateTime

MAX_SKILLS = 25


def _blank_to_none(value: str | None) -> str | None:
    """Optional text: an empty or all-whitespace string clears the value (whitespace is
    trimmed first, by str_strip_whitespace)."""
    return value or None


Headline = Annotated[str | None, Field(max_length=150), AfterValidator(_blank_to_none)]
Bio = Annotated[str | None, Field(max_length=5000), AfterValidator(_blank_to_none)]
Institution = Annotated[str | None, Field(max_length=150), AfterValidator(_blank_to_none)]
City = Annotated[str | None, Field(max_length=100), AfterValidator(_blank_to_none)]
FullName = Annotated[str, Field(min_length=1, max_length=150)]
SkillCode = Annotated[str, Field(min_length=1, max_length=50)]


class ProfileUpdate(BaseModel):
    """PATCH body: only the fields sent are changed. For the optional fields, null or an
    empty string clears the value; full_name can't be cleared."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    full_name: FullName | None = None
    headline: Headline = None
    bio: Bio = None
    institution: Institution = None
    city: City = None

    @model_validator(mode="after")
    def _full_name_not_null(self) -> Self:
        if "full_name" in self.model_fields_set and self.full_name is None:
            raise ValueError("full_name cannot be null")
        return self


class SkillsReplace(BaseModel):
    """PUT body: the complete list of skills you list. Duplicates are collapsed; an empty
    list removes them all."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    skill_codes: list[SkillCode] = Field(description="Skill codes from GET /skills")

    @field_validator("skill_codes")
    @classmethod
    def _collapse_duplicates(cls, codes: list[str]) -> list[str]:
        unique = list(dict.fromkeys(codes))
        if len(unique) > MAX_SKILLS:
            raise ValueError(f"at most {MAX_SKILLS} different skills")
        return unique


class ProfileSkill(BaseModel):
    """`listed`: on the contributor's profile (PUT /contributors/me/skills changes these).
    `verified`: a creator approved their work on an opportunity that required it, first at
    `verified_at`. A skill can be both, or verified without being listed (earned through
    work, ADR 0019); editing the listed skills never removes an earned one."""

    code: str
    name: str
    listed: bool
    verified: bool
    verified_at: UtcDateTime | None


class ContributorProfileRead(BaseModel):
    user_id: int
    full_name: str
    email: str
    headline: str | None
    bio: str | None
    institution: str | None
    city: str | None
    skills: list[ProfileSkill]  # sorted by name
    has_resume: bool
    updated_at: UtcDateTime | None  # None until the first save creates the profile row
