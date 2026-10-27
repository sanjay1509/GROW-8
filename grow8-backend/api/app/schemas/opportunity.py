from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Self

from grow8_common.models import (
    CompensationType,
    OpportunityStatus,
    OrganizationType,
    WorkMode,
)
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import UtcDateTime
from app.schemas.reference import CategoryRead, SkillRead

Text = Annotated[str, Field(min_length=1, max_length=10_000)]
Hours = Annotated[Decimal, Field(gt=0, max_digits=6, decimal_places=2)]
Money = Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2)]


class _OpportunityFields(BaseModel):
    """Fields a creator may fill in. All optional so drafts can be saved incomplete;
    the mandatory ones are enforced when the opportunity is published."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    requirements: Text | None = None
    location: str | None = Field(None, min_length=1, max_length=255)
    work_mode: WorkMode | None = None
    start_date: date | None = None
    end_date: date | None = None
    expected_hours: Hours | None = None
    compensation_type: CompensationType | None = None
    compensation_amount: Money | None = None
    compensation_details: str | None = Field(None, min_length=1, max_length=500)
    applicant_limit: int | None = Field(None, ge=1, le=65535)
    application_deadline: AwareDatetime | None = None
    working_conditions: Text | None = None
    safety_information: Text | None = None
    accessibility_details: Text | None = None

    @model_validator(mode="after")
    def _dates_in_order(self) -> Self:
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class OpportunityCreate(_OpportunityFields):
    title: str = Field(min_length=3, max_length=200)
    description: Text
    category: str = Field(description="Category code, e.g. 'knowledge' or 'community'")
    skills: list[str] = Field(default_factory=list, max_length=20, description="Skill codes")


class OpportunityUpdate(_OpportunityFields):
    """PATCH body: only the fields sent are changed. Send null to clear an optional field."""

    title: str | None = Field(None, min_length=3, max_length=200)
    description: Text | None = None
    category: str | None = None
    skills: list[str] | None = Field(None, max_length=20)

    @model_validator(mode="after")
    def _required_not_null(self) -> Self:
        for name in ("title", "description", "category", "skills"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class OrganizationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    organization_id: int
    name: str
    organization_type: OrganizationType
    city: str | None


class OpportunityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    opportunity_id: int
    title: str
    description: str
    status: OpportunityStatus
    category: CategoryRead
    organization: OrganizationSummary
    skills: list[SkillRead]
    requirements: str | None
    location: str | None
    work_mode: WorkMode | None
    start_date: date | None
    end_date: date | None
    expected_hours: float | None
    compensation_type: CompensationType | None
    compensation_amount: float | None
    compensation_details: str | None
    applicant_limit: int | None
    application_deadline: UtcDateTime | None
    working_conditions: str | None
    safety_information: str | None
    accessibility_details: str | None
    published_at: UtcDateTime | None
    created_at: UtcDateTime
    updated_at: UtcDateTime


class OpportunitySort(StrEnum):
    DEADLINE = "deadline"
    DEADLINE_DESC = "-deadline"
    NEWEST = "newest"
    OLDEST = "oldest"
    HOURS = "hours"
    HOURS_DESC = "-hours"
    COMPENSATION = "compensation"
    COMPENSATION_DESC = "-compensation"
    TITLE = "title"


class OpportunitySearchParams(BaseModel):
    """Query string for listing opportunities. Filters combine with AND;
    repeated `skill` values match opportunities having ANY of those skills."""

    q: str | None = Field(
        None, min_length=1, max_length=100, description="Text in title, description or org name"
    )
    category: str | None = Field(None, description="Category code")
    skill: list[str] = Field(default_factory=list, description="Skill code (repeatable)")
    work_mode: WorkMode | None = None
    compensation_type: CompensationType | None = None
    organization_id: int | None = Field(None, ge=1)
    min_hours: Decimal | None = Field(None, ge=0)
    max_hours: Decimal | None = Field(None, ge=0)
    deadline_before: AwareDatetime | None = Field(
        None, description="Only opportunities whose application deadline is before this time"
    )
    sort: OpportunitySort = OpportunitySort.DEADLINE
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)

    @model_validator(mode="after")
    def _hours_range(self) -> Self:
        if (
            self.min_hours is not None
            and self.max_hours is not None
            and self.min_hours > self.max_hours
        ):
            raise ValueError("min_hours must be less than or equal to max_hours")
        return self


class MyOpportunitySearchParams(OpportunitySearchParams):
    status: list[OpportunityStatus] = Field(
        default_factory=list, description="Status filter (repeatable); default all"
    )
    sort: OpportunitySort = OpportunitySort.NEWEST
