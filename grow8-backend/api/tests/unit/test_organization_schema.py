"""Organization input rules (ADR 0018): trimming, clearing, the fields that can't be
cleared, and only http(s) websites."""

import pytest
from pydantic import ValidationError

from app.schemas.organization import OrganizationUpdate


def test_only_the_fields_sent_are_set() -> None:
    data = OrganizationUpdate.model_validate({"city": " Airdrie "})
    assert (data.model_fields_set, data.city) == ({"city"}, "Airdrie")


@pytest.mark.parametrize("cleared", [None, "", "  "])
def test_optional_fields_can_be_cleared(cleared: str | None) -> None:
    data = OrganizationUpdate.model_validate(
        {"description": cleared, "website": cleared, "city": cleared}
    )
    assert (data.description, data.website, data.city) == (None, None, None)


@pytest.mark.parametrize(
    "body",
    [
        {"name": None},
        {"name": "   "},
        {"name": "x" * 151},
        {"organization_type": None},
        {"organization_type": "charity"},
        {"description": "x" * 5001},
        {"city": "x" * 101},
        {"owner_user_id": 3},
    ],
)
def test_bad_input_is_refused(body: dict) -> None:
    with pytest.raises(ValidationError):
        OrganizationUpdate.model_validate(body)


@pytest.mark.parametrize(
    "website", ["https://example.com", "http://bakery.example/menu?x=1", "HTTPS://Example.com"]
)
def test_http_websites_are_accepted_as_sent(website: str) -> None:
    assert OrganizationUpdate.model_validate({"website": website}).website == website


@pytest.mark.parametrize(
    "website",
    [
        "javascript:alert(1)",
        "ftp://example.com",
        "example.com",
        "https://",
        "http://exa mple.com",
        "https://" + "a" * 250 + ".com",
    ],
)
def test_other_websites_are_refused(website: str) -> None:
    with pytest.raises(ValidationError):
        OrganizationUpdate.model_validate({"website": website})


def test_creating_needs_name_and_type() -> None:
    assert OrganizationUpdate.model_validate(
        {"name": "Corner Café", "organization_type": "small_business"}
    ).can_create()
    assert not OrganizationUpdate.model_validate({"name": "Corner Café"}).can_create()
    assert not OrganizationUpdate.model_validate({"city": "Calgary"}).can_create()
