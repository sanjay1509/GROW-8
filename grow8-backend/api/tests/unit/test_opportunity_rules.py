from datetime import date, datetime
from decimal import Decimal

from grow8_common.models import CompensationType, Opportunity

from app.services.opportunity_rules import (
    dates_out_of_order,
    deadline_has_passed,
    missing_publish_fields,
)


def _complete(**overrides: object) -> Opportunity:
    fields: dict[str, object] = {
        "title": "Task",
        "description": "Do the task",
        "requirements": "None",
        "start_date": date(2027, 1, 1),
        "end_date": date(2027, 1, 31),
        "expected_hours": Decimal("10"),
        "compensation_type": CompensationType.PAID,
        "compensation_amount": Decimal("100"),
        "applicant_limit": 2,
        "application_deadline": datetime(2026, 12, 1),
        "working_conditions": "Office",
        "safety_information": "Standard",
        "accessibility_details": "Step-free",
    }
    fields.update(overrides)
    return Opportunity(**fields)


def test_complete_opportunity_has_nothing_missing() -> None:
    assert missing_publish_fields(_complete()) == []


def test_every_mandatory_disclosure_is_reported_when_missing() -> None:
    opportunity = Opportunity(title="Task", description="Do the task")

    assert missing_publish_fields(opportunity) == [
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
    ]


def test_safety_information_is_mandatory() -> None:
    assert missing_publish_fields(_complete(safety_information=None)) == ["safety_information"]


def test_paid_and_stipend_require_an_amount() -> None:
    for kind in (CompensationType.PAID, CompensationType.STIPEND):
        opportunity = _complete(compensation_type=kind, compensation_amount=None)
        assert missing_publish_fields(opportunity) == ["compensation_amount"]


def test_unpaid_needs_no_amount() -> None:
    opportunity = _complete(compensation_type=CompensationType.UNPAID, compensation_amount=None)
    assert missing_publish_fields(opportunity) == []


def test_deadline_has_passed() -> None:
    opportunity = _complete(application_deadline=datetime(2026, 12, 1))
    assert deadline_has_passed(opportunity, datetime(2026, 12, 1))
    assert not deadline_has_passed(opportunity, datetime(2026, 11, 30))


def test_dates_out_of_order() -> None:
    assert dates_out_of_order(_complete(start_date=date(2027, 2, 1), end_date=date(2027, 1, 1)))
    assert not dates_out_of_order(_complete(start_date=date(2027, 1, 1), end_date=date(2027, 1, 1)))
