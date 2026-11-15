from fastapi.testclient import TestClient

LOGIN = "/api/v1/auth/login"
DEV_PASSWORD = "Grow8Dev!2026"  # seeded dev accounts, see db/init/002_seed.sql


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
