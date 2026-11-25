from typing import Self

from grow8_common.models import OpportunityReport, OpportunityStatus, ReportDecision, ReportReason
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import UtcDateTime
from app.schemas.feedback import Person
from app.services.report_rules import ReportStatus, report_status


def _blank_is_none(text: str | None) -> str | None:
    return text or None


class ReportCreate(BaseModel):
    """A contributor's report about a published opportunity (ADR 0016)."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    reason: ReportReason
    details: str | None = Field(None, max_length=2_000, description="Optional")

    _details = field_validator("details")(_blank_is_none)


class ReportReviewCreate(BaseModel):
    """An admin's decision on a report. Upheld takes the opportunity down. Whether a
    takedown has a reason is a business rule checked by the service."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    decision: ReportDecision
    reason: str | None = Field(
        None,
        max_length=500,
        description="Required when upholding (the creator is told), optional when dismissing",
    )

    _reason = field_validator("reason")(_blank_is_none)


class ReportOpportunity(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    opportunity_id: int
    title: str
    status: OpportunityStatus


class ReportReviewRead(BaseModel):
    """The admin's decision. Which admin decided is not shown."""

    model_config = ConfigDict(from_attributes=True)

    decision: ReportDecision
    reason: str | None
    reviewed_at: UtcDateTime


class ReportRead(BaseModel):
    """A report as its reporter sees it."""

    report_id: int
    opportunity: ReportOpportunity
    reason: ReportReason
    details: str | None
    created_at: UtcDateTime
    status: ReportStatus = Field(description="pending until an admin reviews it")
    review: ReportReviewRead | None = Field(description="The admin's decision, or null")

    @classmethod
    def _fields(cls, report: OpportunityReport) -> dict:
        review = report.review
        return {
            "report_id": report.report_id,
            "opportunity": ReportOpportunity.model_validate(report.opportunity),
            "reason": report.reason,
            "details": report.details,
            "created_at": report.created_at,
            "status": report_status(review.decision if review else None),
            "review": ReportReviewRead.model_validate(review) if review else None,
        }

    @classmethod
    def from_model(cls, report: OpportunityReport) -> Self:
        return cls(**cls._fields(report))


class AdminReportRead(ReportRead):
    """A report as admins see it: with the reporter and how many reports on the same
    opportunity are still open."""

    reporter: Person
    creator: Person
    open_reports_on_opportunity: int

    @classmethod
    def from_report(cls, report: OpportunityReport, open_reports: int) -> Self:
        return cls(
            **cls._fields(report),
            reporter=Person.model_validate(report.reporter),
            creator=Person.model_validate(report.opportunity.organization.owner),
            open_reports_on_opportunity=open_reports,
        )


class TakedownRead(BaseModel):
    """What the owning creator learns about a takedown (ADR 0016 decision 2, #47): when, the
    admin's reason and the report categories. Never the reporters, their own words, or how
    many reported."""

    opportunity_id: int
    taken_down_at: UtcDateTime
    admin_reason: str
    reasons: list[ReportReason]  # distinct categories, alphabetical


class MyReportParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)


class AdminReportParams(MyReportParams):
    status: list[ReportStatus] = Field(
        default_factory=list, description="Status filter (repeatable); default all"
    )
    opportunity_id: int | None = Field(None, ge=1, description="Only reports on this one")
