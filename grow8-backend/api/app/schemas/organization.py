"""The signed-in creator's own organization (ADR 0018)."""

from typing import Annotated, Self
from urllib.parse import urlsplit

from grow8_common.models import OrganizationType
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import UtcDateTime


def _blank_to_none(value: str | None) -> str | None:
    """Optional text: an empty or all-whitespace string clears the value (whitespace is
    trimmed first, by str_strip_whitespace)."""
    return value or None


def _web_address(value: str | None) -> str | None:
    """Only http(s) addresses with a host: the frontend renders the website as a link, so
    `javascript:` and the like must never get in."""
    if value is None:
        return None
    parts = urlsplit(value)
    if parts.scheme.lower() not in ("http", "https") or not parts.hostname:
        raise ValueError("must be an http:// or https:// address")
    if any(c.isspace() for c in value):
        raise ValueError("must not contain spaces")
    return value


Description = Annotated[str | None, Field(max_length=5000), AfterValidator(_blank_to_none)]
City = Annotated[str | None, Field(max_length=100), AfterValidator(_blank_to_none)]
Website = Annotated[
    str | None,
    Field(max_length=255, examples=["https://example.com"]),
    AfterValidator(_blank_to_none),
    AfterValidator(_web_address),
]

_REQUIRED = ("name", "organization_type")


class OrganizationUpdate(BaseModel):
    """PATCH body: only the fields sent are changed. For the optional fields, null or an
    empty string clears the value; name and organization_type can't be cleared."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(None, min_length=1, max_length=150)
    organization_type: OrganizationType | None = None
    description: Description = None
    website: Website = None
    city: City = None

    @model_validator(mode="after")
    def _required_not_null(self) -> Self:
        for field in _REQUIRED:
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self

    def can_create(self) -> bool:
        """Whether this body is enough to create a missing organization."""
        return all(field in self.model_fields_set for field in _REQUIRED)


class OrganizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: int
    name: str
    organization_type: OrganizationType
    description: str | None
    website: str | None
    city: str | None
    updated_at: UtcDateTime
