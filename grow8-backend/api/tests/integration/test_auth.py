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
