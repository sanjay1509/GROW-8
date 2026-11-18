"""Case-catalog smoke and negative coverage for APIs added beyond the approved catalog."""

import pytest

from tests.fakes import FakePublisher

from .conftest import (
    DEV_PASSWORD,
    EMAILS,
    current_parameters,
    expect,
    ids,
    page,
)

OPPORTUNITIES_URL = "/api/v1/opportunities"
APPLICATIONS_URL = "/api/v1/applications"


def _apply(api, headers, opportunity_id: int, **body) -> int:
    response = api.post(
        f"{OPPORTUNITIES_URL}/{opportunity_id}/applications",
        json=body,
        headers=headers,
    )
    return expect(response, 201)["application_id"]


def _status(response, expected: int, code: str | None = None):
    return expect(response, expected, code)


@pytest.mark.parametrize("case_id", current_parameters("CUR-PASSWORD-"))
def test_change_password(case_id, api, contributor):
    new_password = "CurrentApi!2026"
    if case_id.endswith("001"):
        changed = api.post(
            "/api/v1/auth/change-password",
            json={"current_password": DEV_PASSWORD, "new_password": new_password},
            headers=contributor,
        )
        expect(changed, 200)
        _status(api.post("/api/v1/auth/login", json={
            "email": EMAILS["contributor"], "password": DEV_PASSWORD,
        }), 401)
        _status(api.post("/api/v1/auth/login", json={
            "email": EMAILS["contributor"], "password": new_password,
        }), 200)
    elif case_id.endswith("002"):
        _status(api.post(
            "/api/v1/auth/change-password",
            json={"current_password": "wrong", "new_password": new_password},
            headers=contributor,
        ), 401, "INVALID_CURRENT_PASSWORD")
    elif case_id.endswith("003"):
        _status(api.post(
            "/api/v1/auth/change-password",
            json={"current_password": DEV_PASSWORD, "new_password": DEV_PASSWORD},
            headers=contributor,
        ), 422, "PASSWORD_UNCHANGED")
    elif case_id.endswith("004"):
        _status(api.post(
            "/api/v1/auth/change-password",
            json={"current_password": DEV_PASSWORD, "new_password": new_password},
        ), 401, "AUTH_REQUIRED")
    elif case_id.endswith("005"):
        _status(api.post(
            "/api/v1/auth/change-password",
            json={"current_password": DEV_PASSWORD, "new_password": "é" * 37},
            headers=contributor,
        ), 422, "VALIDATION_ERROR")
    elif case_id.endswith("006"):
        password = "Aa1!" * 18
        expect(api.post(
            "/api/v1/auth/change-password",
            json={"current_password": DEV_PASSWORD, "new_password": password},
            headers=contributor,
        ), 200)
        _status(api.post("/api/v1/auth/login", json={
            "email": EMAILS["contributor"], "password": password,
        }), 200)
    else:
        raise AssertionError(f"Unknown current password case: {case_id}")


@pytest.mark.parametrize("case_id", current_parameters("CUR-APPLY-"))
def test_apply_to_opportunity(
    case_id, api, contributor, jordan, sam, bakery, seeded_db, publisher: FakePublisher
):
    if case_id.endswith("001"):
        response = api.post(
            f"{OPPORTUNITIES_URL}/1/applications",
            json={"motivation": "  I type fast and love bread.  "},
            headers={**contributor, "X-Request-ID": "apply-current-1"},
        )
        body = expect(response, 201)
        assert body["status"] == "pending"
        assert body["motivation"] == "I type fast and love bread."
        assert body["decided_at"] is None
        assert body["opportunity"]["opportunity_id"] == 1
        assert body["applicant"]["user_id"] == 5
        assert "email" not in body["applicant"]
        event = publisher.events[-1]
        assert event.event_type == "APPLICATION_SUBMITTED"
        assert event.correlation_id == "apply-current-1"
        assert event.payload["application_id"] == body["application_id"]
    elif case_id.endswith("002"):
        assert expect(api.post(
            f"{OPPORTUNITIES_URL}/1/applications", json={}, headers=contributor,
        ), 201)["motivation"] is None
        _status(api.post(
            f"{OPPORTUNITIES_URL}/8/applications",
            json={"resume": "cv.pdf"},
            headers=contributor,
        ), 422, "VALIDATION_ERROR")
    elif case_id.endswith("003"):
        application_id = _apply(api, contributor, 1)
        duplicate = api.post(
            f"{OPPORTUNITIES_URL}/1/applications", json={}, headers=contributor,
        )
        assert _status(duplicate, 409, "APPLICATION_DUPLICATE")["error"]["details"] == {
            "application_id": application_id,
        }
        assert len(publisher.events) == 1
    elif case_id.endswith("004"):
        application_id = _apply(api, contributor, 1)
        expect(api.post(
            f"{APPLICATIONS_URL}/{application_id}/withdraw", headers=contributor,
        ), 200)
        _status(api.post(
            f"{OPPORTUNITIES_URL}/1/applications", json={}, headers=contributor,
        ), 409, "APPLICATION_DUPLICATE")
    elif case_id.endswith("005"):
        _apply(api, contributor, 2)
        _status(api.post(
            f"{OPPORTUNITIES_URL}/2/applications", json={}, headers=jordan,
        ), 409, "APPLICANT_LIMIT_REACHED")
    elif case_id.endswith("006"):
        for opportunity_id, status, code in (
            (10, 409, "APPLICATION_DEADLINE_PASSED"),
            (11, 409, "OPPORTUNITY_NOT_OPEN"),
            (14, 404, "OPPORTUNITY_NOT_FOUND"),
            (9999, 404, "OPPORTUNITY_NOT_FOUND"),
        ):
            _status(api.post(
                f"{OPPORTUNITIES_URL}/{opportunity_id}/applications",
                json={},
                headers=contributor,
            ), status, code)
    elif case_id.endswith("007"):
        _status(api.post(
            f"{OPPORTUNITIES_URL}/8/applications", json={}, headers=bakery,
        ), 403, "ROLE_FORBIDDEN")
        _status(api.post(
            f"{OPPORTUNITIES_URL}/8/applications", json={},
        ), 401, "AUTH_REQUIRED")
    elif case_id.endswith("008"):
        with seeded_db.cursor() as cursor:
            cursor.execute("DELETE FROM contributor_profile WHERE user_id = 7")
        _status(api.post(
            f"{OPPORTUNITIES_URL}/8/applications", json={}, headers=sam,
        ), 409, "CONTRIBUTOR_PROFILE_REQUIRED")
        assert publisher.events == []
    else:
        raise AssertionError(f"Unknown application submission case: {case_id}")


@pytest.mark.parametrize("case_id", current_parameters("CUR-OPPLIST-"))
def test_list_opportunity_applications(case_id, api, contributor, jordan, bakery, events_org):
    if case_id.endswith("001"):
        _apply(api, contributor, 1)
        _apply(api, jordan, 1)
        _apply(api, jordan, 8)
        result = page(api.get(
            f"{OPPORTUNITIES_URL}/1/applications",
            headers=bakery,
            params={"limit": 1, "offset": 1},
        ), total=2, limit=1, offset=1)
        assert len(result["items"]) == 1
        assert result["items"][0]["opportunity"]["opportunity_id"] == 1
    elif case_id.endswith("002"):
        _status(api.get(f"{OPPORTUNITIES_URL}/1/applications", headers=events_org),
                403, "NOT_OPPORTUNITY_OWNER")
        _status(api.get(f"{OPPORTUNITIES_URL}/1/applications", headers=contributor),
                403, "ROLE_FORBIDDEN")
        _status(api.get(f"{OPPORTUNITIES_URL}/1/applications"),
                401, "AUTH_REQUIRED")
    elif case_id.endswith("003"):
        for opportunity_id in (14, 9999):
            _status(api.get(
                f"{OPPORTUNITIES_URL}/{opportunity_id}/applications", headers=events_org,
            ), 404, "OPPORTUNITY_NOT_FOUND")
    else:
        raise AssertionError(f"Unknown opportunity-application listing case: {case_id}")


@pytest.mark.parametrize("case_id", current_parameters("CUR-MINEAPP-"))
def test_list_my_applications(case_id, api, contributor, jordan, bakery):
    if case_id.endswith("001"):
        mine = {
            _apply(api, contributor, 1),
            _apply(api, contributor, 8),
        }
        _apply(api, jordan, 1)
        result = page(api.get(f"{APPLICATIONS_URL}/mine", headers=contributor), total=2)
        assert {item["application_id"] for item in result["items"]} == mine
    elif case_id.endswith("002"):
        kept = _apply(api, contributor, 1)
        withdrawn = _apply(api, contributor, 8)
        expect(api.post(
            f"{APPLICATIONS_URL}/{withdrawn}/withdraw", headers=contributor,
        ), 200)
        result = page(api.get(
            f"{APPLICATIONS_URL}/mine",
            headers=contributor,
            params={"status": "pending"},
        ), total=1)
        assert [item["application_id"] for item in result["items"]] == [kept]
    elif case_id.endswith("003"):
        _status(api.get(f"{APPLICATIONS_URL}/mine"), 401, "AUTH_REQUIRED")
        _status(api.get(f"{APPLICATIONS_URL}/mine", headers=bakery), 403, "ROLE_FORBIDDEN")
    else:
        raise AssertionError(f"Unknown own-application listing case: {case_id}")


@pytest.mark.parametrize("case_id", current_parameters("CUR-RECEIVED-"))
def test_list_received_applications(case_id, api, contributor, jordan, bakery, events_org):
    if case_id.endswith("001"):
        bakery_application = _apply(api, contributor, 1)
        yyc_application = _apply(api, jordan, 8)
        bakery_page = page(api.get(f"{APPLICATIONS_URL}/received", headers=bakery), total=1)
        yyc_page = page(api.get(f"{APPLICATIONS_URL}/received", headers=events_org), total=1)
        assert bakery_page["items"][0]["application_id"] == bakery_application
        assert yyc_page["items"][0]["application_id"] == yyc_application
    elif case_id.endswith("002"):
        pending = _apply(api, contributor, 1)
        accepted = _apply(api, jordan, 2)
        expect(api.post(
            f"{APPLICATIONS_URL}/{accepted}/decision",
            json={"decision": "accepted"},
            headers=bakery,
        ), 200)
        result = page(api.get(
            f"{APPLICATIONS_URL}/received",
            headers=bakery,
            params={"opportunity_id": 1, "status": "pending"},
        ), total=1)
        assert result["items"][0]["application_id"] == pending
    elif case_id.endswith("003"):
        _status(api.get(f"{APPLICATIONS_URL}/received"), 401, "AUTH_REQUIRED")
        _status(api.get(
            f"{APPLICATIONS_URL}/received", headers=contributor,
        ), 403, "ROLE_FORBIDDEN")
        _status(api.get(
            f"{APPLICATIONS_URL}/received",
            headers=bakery,
            params={"opportunity_id": 0},
        ), 422, "VALIDATION_ERROR")
    else:
        raise AssertionError(f"Unknown received-application listing case: {case_id}")


@pytest.mark.parametrize("case_id", current_parameters("CUR-APPDETAIL-"))
def test_get_application(case_id, api, contributor, jordan, bakery, events_org):
    application_id = _apply(api, contributor, 1)
    url = f"{APPLICATIONS_URL}/{application_id}"
    if case_id.endswith("001"):
        assert expect(api.get(url, headers=contributor), 200)["application_id"] == application_id
    elif case_id.endswith("002"):
        assert expect(api.get(url, headers=bakery), 200)["application_id"] == application_id
    elif case_id.endswith("003"):
        for headers in (jordan, events_org):
            _status(api.get(url, headers=headers), 404, "APPLICATION_NOT_FOUND")
        _status(api.get(f"{APPLICATIONS_URL}/9999", headers=bakery),
                404, "APPLICATION_NOT_FOUND")
    elif case_id.endswith("004"):
        _status(api.get(url), 401, "AUTH_REQUIRED")
        _status(api.get(f"{APPLICATIONS_URL}/0", headers=bakery),
                422, "VALIDATION_ERROR")
    else:
        raise AssertionError(f"Unknown application-detail case: {case_id}")


@pytest.mark.parametrize("case_id", current_parameters("CUR-DECISION-"))
def test_decide_application(case_id, api, contributor, bakery, events_org, publisher):
    application_id = _apply(api, contributor, 1)
    url = f"{APPLICATIONS_URL}/{application_id}/decision"
    if case_id.endswith("001"):
        response = expect(api.post(
            url,
            json={"decision": "accepted"},
            headers={**bakery, "X-Request-ID": "decision-current-1"},
        ), 200)
        assert response["status"] == "accepted"
        assert publisher.events[-1].event_type == "APPLICATION_DECIDED"
        assert publisher.events[-1].correlation_id == "decision-current-1"
    elif case_id.endswith("002"):
        response = expect(api.post(
            url, json={"decision": "rejected"}, headers=bakery,
        ), 200)
        assert response["status"] == "rejected"
    elif case_id.endswith("003"):
        expect(api.post(url, json={"decision": "rejected"}, headers=bakery), 200)
        _status(api.post(
            url, json={"decision": "accepted"}, headers=bakery,
        ), 409, "APPLICATION_NOT_PENDING")
    elif case_id.endswith("004"):
        expect(api.post(
            f"{APPLICATIONS_URL}/{application_id}/withdraw", headers=contributor,
        ), 200)
        _status(api.post(
            url, json={"decision": "accepted"}, headers=bakery,
        ), 409, "APPLICATION_NOT_PENDING")
    elif case_id.endswith("005"):
        _status(api.post(
            url, json={"decision": "accepted"}, headers=events_org,
        ), 404, "APPLICATION_NOT_FOUND")
        _status(api.post(
            url, json={"decision": "accepted"}, headers=contributor,
        ), 403, "ROLE_FORBIDDEN")
        _status(api.post(url, json={"decision": "accepted"}), 401, "AUTH_REQUIRED")
    elif case_id.endswith("006"):
        _status(api.post(
            url, json={"decision": "withdrawn"}, headers=bakery,
        ), 422, "VALIDATION_ERROR")
    else:
        raise AssertionError(f"Unknown application-decision case: {case_id}")


@pytest.mark.parametrize("case_id", current_parameters("CUR-WITHDRAW-"))
def test_withdraw_application(case_id, api, contributor, jordan, bakery, seeded_db, publisher):
    application_id = _apply(api, contributor, 1)
    url = f"{APPLICATIONS_URL}/{application_id}/withdraw"
    if case_id.endswith("001"):
        response = expect(api.post(
            url,
            headers={**contributor, "X-Request-ID": "withdraw-current-1"},
        ), 200)
        assert response["status"] == "withdrawn"
        assert publisher.events[-1].event_type == "APPLICATION_WITHDRAWN"
        assert publisher.events[-1].correlation_id == "withdraw-current-1"
    elif case_id.endswith("002"):
        accepted = _apply(api, contributor, 2)
        expect(api.post(
            f"{APPLICATIONS_URL}/{accepted}/decision",
            json={"decision": "accepted"},
            headers=bakery,
        ), 200)
        assert expect(api.post(
            f"{APPLICATIONS_URL}/{accepted}/withdraw", headers=contributor,
        ), 200)["status"] == "withdrawn"
    elif case_id.endswith("003"):
        expect(api.post(url, headers=contributor), 200)
        _status(api.post(url, headers=contributor), 409, "APPLICATION_NOT_ACTIVE")
        rejected = _apply(api, jordan, 1)
        expect(api.post(
            f"{APPLICATIONS_URL}/{rejected}/decision",
            json={"decision": "rejected"},
            headers=bakery,
        ), 200)
        _status(api.post(
            f"{APPLICATIONS_URL}/{rejected}/withdraw", headers=jordan,
        ), 409, "APPLICATION_NOT_ACTIVE")
    elif case_id.endswith("004"):
        expect(api.post(
            f"{APPLICATIONS_URL}/{application_id}/decision",
            json={"decision": "accepted"},
            headers=bakery,
        ), 200)
        with seeded_db.cursor() as cursor:
            cursor.execute(
                "INSERT INTO work_submission (application_id, description, hours_claimed) "
                "VALUES (%s, 'QA submitted work.', 1)",
                (application_id,),
            )
        _status(api.post(
            f"{APPLICATIONS_URL}/{application_id}/withdraw", headers=contributor,
        ), 409, "WORK_ALREADY_SUBMITTED")
    elif case_id.endswith("005"):
        _status(api.post(url), 401, "AUTH_REQUIRED")
        _status(api.post(url, headers=bakery), 403, "ROLE_FORBIDDEN")
        _status(api.post(
            f"{APPLICATIONS_URL}/{application_id}/withdraw", headers=jordan,
        ), 404, "APPLICATION_NOT_FOUND")
    else:
        raise AssertionError(f"Unknown application-withdrawal case: {case_id}")


@pytest.mark.parametrize("case_id", current_parameters("CUR-CLOSE-"))
def test_close_opportunity(
    case_id, api, contributor, jordan, bakery, events_org, publisher, seeded_db
):
    if case_id.endswith("001"):
        application_id = _apply(api, contributor, 1)
        sent = len(publisher.events)
        closed = expect(api.post(f"{OPPORTUNITIES_URL}/1/close", headers=bakery), 200)
        assert closed["status"] == "closed"
        assert len(publisher.events) == sent
        _status(api.post(
            f"{OPPORTUNITIES_URL}/1/applications", json={}, headers=jordan,
        ), 409, "OPPORTUNITY_NOT_OPEN")
        decision = expect(api.post(
            f"{APPLICATIONS_URL}/{application_id}/decision",
            json={"decision": "accepted"},
            headers=bakery,
        ), 200)
        assert decision["opportunity"]["status"] == "closed"
    elif case_id.endswith("002"):
        expect(api.post(f"{OPPORTUNITIES_URL}/1/close", headers=bakery), 200)
        with seeded_db.cursor() as cursor:
            cursor.execute(
                "UPDATE opportunity SET status = 'cancelled' WHERE opportunity_id = 2"
            )
        seeded_db.commit()
        _status(api.post(f"{OPPORTUNITIES_URL}/1/close", headers=bakery),
                409, "OPPORTUNITY_NOT_OPEN")
        _status(api.post(f"{OPPORTUNITIES_URL}/14/close", headers=bakery),
                409, "OPPORTUNITY_NOT_OPEN")
        _status(api.post(f"{OPPORTUNITIES_URL}/2/close", headers=bakery),
                409, "OPPORTUNITY_NOT_OPEN")
    elif case_id.endswith("003"):
        _status(api.post(f"{OPPORTUNITIES_URL}/1/close"), 401, "AUTH_REQUIRED")
        _status(api.post(
            f"{OPPORTUNITIES_URL}/1/close", headers=contributor,
        ), 403, "ROLE_FORBIDDEN")
        _status(api.post(
            f"{OPPORTUNITIES_URL}/1/close", headers=events_org,
        ), 403, "NOT_OPPORTUNITY_OWNER")
    elif case_id.endswith("004"):
        expect(api.post(f"{OPPORTUNITIES_URL}/1/close", headers=bakery), 200)
        public = page(api.get(OPPORTUNITIES_URL, params={"limit": 100}))
        assert 1 not in ids(public["items"])
        assert expect(api.get(f"{OPPORTUNITIES_URL}/1"), 200)["status"] == "closed"
    else:
        raise AssertionError(f"Unknown opportunity-close case: {case_id}")


@pytest.mark.parametrize("case_id", current_parameters("CUR-CANCEL-"))
def test_cancel_opportunity(
    case_id, api, contributor, jordan, bakery, events_org, seeded_db, publisher
):
    if case_id.endswith("001"):
        pending = _apply(api, contributor, 1)
        accepted = _apply(api, jordan, 1)
        expect(api.post(
            f"{APPLICATIONS_URL}/{accepted}/decision",
            json={"decision": "accepted"},
            headers=bakery,
        ), 200)
        response = expect(api.post(
            f"{OPPORTUNITIES_URL}/1/cancel",
            headers={**bakery, "X-Request-ID": "cancel-current-1"},
        ), 200)
        assert response["status"] == "cancelled"
        assert publisher.events[-1].event_type == "OPPORTUNITY_CANCELLED"
        assert publisher.events[-1].correlation_id == "cancel-current-1"
        for application_id, status in ((pending, "pending"), (accepted, "accepted")):
            application = expect(api.get(
                f"{APPLICATIONS_URL}/{application_id}", headers=bakery,
            ), 200)
            assert application["status"] == status
            assert application["opportunity"]["status"] == "cancelled"
    elif case_id.endswith("002"):
        expect(api.post(f"{OPPORTUNITIES_URL}/1/close", headers=bakery), 200)
        assert expect(api.post(f"{OPPORTUNITIES_URL}/1/cancel", headers=bakery),
                      200)["status"] == "cancelled"
    elif case_id.endswith("003"):
        _status(api.post(f"{OPPORTUNITIES_URL}/14/cancel", headers=bakery),
                409, "OPPORTUNITY_NOT_PUBLISHED")
        expect(api.post(f"{OPPORTUNITIES_URL}/1/cancel", headers=bakery), 200)
        _status(api.post(f"{OPPORTUNITIES_URL}/1/cancel", headers=bakery),
                409, "OPPORTUNITY_CANCELLED")
    elif case_id.endswith("004"):
        application_id = _apply(api, contributor, 1)
        expect(api.post(
            f"{APPLICATIONS_URL}/{application_id}/decision",
            json={"decision": "accepted"},
            headers=bakery,
        ), 200)
        with seeded_db.cursor() as cursor:
            cursor.execute(
                "INSERT INTO work_submission (application_id, description, hours_claimed) "
                "VALUES (%s, 'QA submitted work.', 1)",
                (application_id,),
            )
        sent = len(publisher.events)
        _status(api.post(f"{OPPORTUNITIES_URL}/1/cancel", headers=bakery),
                409, "WORK_ALREADY_SUBMITTED")
        assert expect(api.get(f"{OPPORTUNITIES_URL}/1"), 200)["status"] == "open"
        assert len(publisher.events) == sent
    elif case_id.endswith("005"):
        _status(api.post(f"{OPPORTUNITIES_URL}/1/cancel"), 401, "AUTH_REQUIRED")
        _status(api.post(
            f"{OPPORTUNITIES_URL}/1/cancel", headers=contributor,
        ), 403, "ROLE_FORBIDDEN")
        _status(api.post(
            f"{OPPORTUNITIES_URL}/1/cancel", headers=events_org,
        ), 403, "NOT_OPPORTUNITY_OWNER")
    elif case_id.endswith("006"):
        application_id = _apply(api, contributor, 1)
        another = _apply(api, jordan, 1)
        expect(api.post(f"{OPPORTUNITIES_URL}/1/cancel", headers=bakery), 200)
        assert expect(api.post(
            f"{APPLICATIONS_URL}/{application_id}/withdraw", headers=contributor,
        ), 200)["status"] == "withdrawn"
        _status(api.post(
            f"{APPLICATIONS_URL}/{another}/decision",
            json={"decision": "accepted"},
            headers=bakery,
        ), 409, "OPPORTUNITY_CANCELLED")
    else:
        raise AssertionError(f"Unknown opportunity-cancel case: {case_id}")


@pytest.mark.parametrize("case_id", current_parameters("CUR-OPPDELETE-"))
def test_delete_opportunity(case_id, api, bakery, contributor):
    if case_id.endswith("001"):
        response = api.delete(f"{OPPORTUNITIES_URL}/14", headers=bakery)
        assert response.status_code == 204, response.text
        _status(api.get(f"{OPPORTUNITIES_URL}/14", headers=bakery),
                404, "OPPORTUNITY_NOT_FOUND")
    elif case_id.endswith("002"):
        _status(api.delete(f"{OPPORTUNITIES_URL}/1", headers=bakery),
                409, "OPPORTUNITY_NOT_DRAFT")
        assert expect(api.get(f"{OPPORTUNITIES_URL}/1"), 200)["opportunity_id"] == 1
    elif case_id.endswith("003"):
        _status(api.delete(f"{OPPORTUNITIES_URL}/14"), 401, "AUTH_REQUIRED")
        _status(api.delete(
            f"{OPPORTUNITIES_URL}/14", headers=contributor,
        ), 403, "ROLE_FORBIDDEN")
        _status(api.delete(
            f"{OPPORTUNITIES_URL}/15", headers=bakery,
        ), 404, "OPPORTUNITY_NOT_FOUND")
        _status(api.delete(
            f"{OPPORTUNITIES_URL}/8", headers=bakery,
        ), 403, "NOT_OPPORTUNITY_OWNER")
    else:
        raise AssertionError(f"Unknown opportunity-deletion case: {case_id}")
