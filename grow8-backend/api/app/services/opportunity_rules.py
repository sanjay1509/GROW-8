"""Pure publishing rules (no DB, no HTTP) so they are easy to unit test."""

from datetime import datetime

from grow8_common.models import CompensationType, Opportunity

# Disclosures required before an opportunity can be published (CLAUDE.md section 8).
# category, title and description are NOT NULL columns, so they are always present.
MANDATORY_PUBLISH_FIELDS: tuple[str, ...] = (
    "requirements",
    "start_date",
    "end_date",
    "expected_hours",
    "compensation_type",
    "applicant_limit",
    "application_deadline",
    "working_conditions",
    "safety_information",
    "accessibility_details",
)

_AMOUNT_REQUIRED = {CompensationType.PAID, CompensationType.STIPEND}


def missing_publish_fields(opportunity: Opportunity) -> list[str]:
    missing = [
        name
        for name in MANDATORY_PUBLISH_FIELDS
        if getattr(opportunity, name) in (None, "")
    ]
    if (
        opportunity.compensation_type in _AMOUNT_REQUIRED
        and opportunity.compensation_amount is None
    ):
        missing.append("compensation_amount")
    return missing


def deadline_has_passed(opportunity: Opportunity, now: datetime) -> bool:
    return (
        opportunity.application_deadline is not None and opportunity.application_deadline <= now
    )


def dates_out_of_order(opportunity: Opportunity) -> bool:
    return bool(
        opportunity.start_date
        and opportunity.end_date
        and opportunity.end_date < opportunity.start_date
    )
