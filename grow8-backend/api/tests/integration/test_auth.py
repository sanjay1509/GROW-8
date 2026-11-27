from typing import Any

import bcrypt
from fastapi.testclient import TestClient

LOGIN = "/api/v1/auth/login"
REGISTER = "/api/v1/auth/register"
DEV_PASSWORD = "Grow8Dev!2026"  # seeded dev accounts, see db/init/002_seed.sql


def test_register_contributor_creates_profile_and_signs_them_in(client: TestClient) -> None:
    response = client.post(
        REGISTER,
        json={
            "email": "  new.contributor@example.com ",
            "full_name": "New Contributor",
            "password": "Strong-pass-2026",
            "role": "contributor",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "new.contributor@example.com"
    assert body["user"]["role"] == "contributor"
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    assert client.get("/api/v1/auth/me", headers=headers).json()["full_name"] == "New Contributor"
    profile = client.get("/api/v1/contributors/me/profile", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["user_id"] == body["user"]["user_id"]


def test_register_creator_and_sign_them_in(client: TestClient) -> None:
    response = client.post(
        REGISTER,
        json={
            "email": "new.creator@example.com",
            "full_name": "New Creator",
            "password": "Strong-pass-2026",
            "role": "creator",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["role"] == "creator"
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    assert client.get("/api/v1/opportunities/mine", headers=headers).status_code == 200


def test_register_rejects_duplicate_email(client: TestClient) -> None:
    body = {
        "email": "new.user@example.com",
        "full_name": "New User",
        "password": "Strong-pass-2026",
        "role": "contributor",
    }
    assert client.post(REGISTER, json=body).status_code == 201

    duplicate = client.post(REGISTER, json=body)
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


def test_register_rejects_admin_self_registration_and_short_password(
    client: TestClient,
) -> None:
    body = {
        "email": "admin.signup@example.com",
        "full_name": "Not An Admin",
        "password": "Strong-pass-2026",
        "role": "admin",
    }
    assert client.post(REGISTER, json=body).status_code == 422

    body["role"] = "contributor"
    body["password"] = "short"
    assert client.post(REGISTER, json=body).status_code == 422


def test_login_returns_token_and_user(client: TestClient) -> None:
    credentials = {"email": "maple.bakery@grow8.dev", "password": DEV_PASSWORD}
    response = client.post(LOGIN, json=credentials)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"] == {
        "user_id": 2,
        "email": "maple.bakery@grow8.dev",
        "full_name": "Priya Nair",
        "role": "creator",
    }
    assert "password_hash" not in response.text


def test_wrong_password_is_401_with_error_body(client: TestClient) -> None:
    response = client.post(LOGIN, json={"email": "maple.bakery@grow8.dev", "password": "nope"})

    assert response.status_code == 401
    assert response.json() == {
        "error": {"code": "INVALID_CREDENTIALS", "message": "Incorrect email or password"}
    }


def test_unknown_email_gives_same_error_as_wrong_password(client: TestClient) -> None:
    response = client.post(LOGIN, json={"email": "nobody@grow8.dev", "password": DEV_PASSWORD})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_me_requires_a_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_REQUIRED"


def test_me_rejects_a_bad_token(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-jwt"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"


def test_me_returns_the_caller(client: TestClient, contributor: dict[str, str]) -> None:
    response = client.get("/api/v1/auth/me", headers=contributor)

    assert response.status_code == 200
    assert response.json()["role"] == "contributor"


# --- change password ----------------------------------------------------------

CHANGE = "/api/v1/auth/change-password"


def test_change_password_then_login_with_the_new_one(
    client: TestClient, contributor: dict[str, str]
) -> None:
    body = {"current_password": DEV_PASSWORD, "new_password": "BrandNew!2026"}
    response = client.post(CHANGE, json=body, headers=contributor)

    assert response.status_code == 200
    old = client.post(LOGIN, json={"email": "alex.chen@grow8.dev", "password": DEV_PASSWORD})
    new = client.post(LOGIN, json={"email": "alex.chen@grow8.dev", "password": "BrandNew!2026"})
    assert old.status_code == 401
    assert new.status_code == 200


def test_change_password_requires_the_current_password(
    client: TestClient, contributor: dict[str, str]
) -> None:
    body = {"current_password": "wrong", "new_password": "BrandNew!2026"}
    response = client.post(CHANGE, json=body, headers=contributor)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CURRENT_PASSWORD"


def test_change_password_rejects_reusing_the_current_password(
    client: TestClient, contributor: dict[str, str]
) -> None:
    body = {"current_password": DEV_PASSWORD, "new_password": DEV_PASSWORD}
    response = client.post(CHANGE, json=body, headers=contributor)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "PASSWORD_UNCHANGED"


def test_change_password_requires_a_token(client: TestClient) -> None:
    body = {"current_password": DEV_PASSWORD, "new_password": "BrandNew!2026"}

    assert client.post(CHANGE, json=body).status_code == 401


def test_new_password_is_limited_to_72_bytes(
    client: TestClient, contributor: dict[str, str]
) -> None:
    accented = "é" * 37  # 37 characters but 74 bytes
    body = {"current_password": DEV_PASSWORD, "new_password": accented}

    response = client.post(CHANGE, json=body, headers=contributor)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "72 bytes" in response.text


def test_a_72_byte_password_works(client: TestClient, contributor: dict[str, str]) -> None:
    longest = "Aa1!" * 18  # exactly 72 bytes
    body = {"current_password": DEV_PASSWORD, "new_password": longest}

    assert client.post(CHANGE, json=body, headers=contributor).status_code == 200
    login = client.post(LOGIN, json={"email": "alex.chen@grow8.dev", "password": longest})
    assert login.status_code == 200


def test_user_with_an_over_long_password_from_before_the_cap(
    client: TestClient, seeded_db: Any
) -> None:
    """A hash bcrypt 4.x made from a 100-character password (it used the first 72 bytes)
    still signs in, and "changing" to those 72 bytes counts as unchanged."""
    long_password = "Long-pass-" * 10
    old_hash = bcrypt.hashpw(long_password.encode()[:72], bcrypt.gensalt()).decode()
    with seeded_db.cursor() as cur:
        cur.execute("UPDATE user_account SET password_hash = %s WHERE user_id = 5", (old_hash,))

    login = client.post(LOGIN, json={"email": "alex.chen@grow8.dev", "password": long_password})
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    body = {"current_password": long_password, "new_password": long_password[:72]}
    response = client.post(CHANGE, json=body, headers=headers)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "PASSWORD_UNCHANGED"
