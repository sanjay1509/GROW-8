"""Invalid apply form input is a 422 VALIDATION_ERROR with field details, never a 500
(#46). Opportunity 1 is open and seeded with no applications."""

import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.fakes import FakePublisher

URL = "/api/v1/opportunities/1/applications"


def _apply(client: TestClient, headers: dict[str, str], **fields: str) -> Any:
    return client.post(URL, data=fields, headers=headers)


@pytest.mark.parametrize(
    ("fields", "loc"),
    [
        ({"motivation": "x" * 5001}, ["body", "motivation"]),
        (
            {"application_details": json.dumps({"years": 3})},
            ["body", "application_details", "years"],
        ),
        ({"application_details": "[1, 2]"}, ["body", "application_details"]),
        ({"application_details": "null"}, ["body", "application_details"]),
        ({"application_details": "not json"}, ["body", "application_details"]),
    ],
)
def test_bad_input_is_a_422_with_the_field(
    client: TestClient,
    contributor: dict[str, str],
    publisher: FakePublisher,
    fields: dict[str, str],
    loc: list[str],
) -> None:
    response = _apply(client, contributor, **fields)

    assert response.status_code == 422, response.text
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert loc in [d["loc"] for d in error["details"]]
    assert publisher.events == []
    # Nothing was created: the same contributor can still apply.
    assert _apply(client, contributor).status_code == 201


@pytest.mark.parametrize("motivation", ["", "   "])
def test_an_empty_motivation_field_means_none(
    client: TestClient, contributor: dict[str, str], motivation: str
) -> None:
    response = _apply(client, contributor, motivation=motivation)

    assert response.status_code == 201, response.text
    assert response.json()["motivation"] is None


def test_motivation_is_trimmed(client: TestClient, contributor: dict[str, str]) -> None:
    response = _apply(client, contributor, motivation="  I type fast.  ")
    assert response.json()["motivation"] == "I type fast."


def test_oversized_details_are_a_422(client: TestClient, contributor: dict[str, str]) -> None:
    details = json.dumps({"experience": "x" * 2001})
    response = _apply(client, contributor, application_details=details)

    assert response.status_code == 422, response.text
    locs = [d["loc"] for d in response.json()["error"]["details"]]
    assert ["body", "application_details", "experience"] in locs
