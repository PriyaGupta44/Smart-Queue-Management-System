"""Tests for rate limiting on auth endpoints."""


def test_login_is_rate_limited_after_too_many_attempts(rate_limited_client):
    for _ in range(10):
        rate_limited_client.post(
            "/auth/login", data={"email": "nobody@example.com", "password": "wrongpassword"}
        )

    response = rate_limited_client.post(
        "/auth/login", data={"email": "nobody@example.com", "password": "wrongpassword"}
    )

    assert response.status_code == 429


def test_register_is_rate_limited_after_too_many_attempts(rate_limited_client):
    for i in range(5):
        rate_limited_client.post(
            "/auth/register",
            data={
                "full_name": f"Spammer {i}",
                "email": f"spammer{i}@example.com",
                "password": "password123",
                "confirm_password": "password123",
            },
        )

    response = rate_limited_client.post(
        "/auth/register",
        data={
            "full_name": "One More",
            "email": "onemore@example.com",
            "password": "password123",
            "confirm_password": "password123",
        },
    )

    assert response.status_code == 429


def test_forgot_password_is_rate_limited_after_too_many_attempts(rate_limited_client):
    for _ in range(3):
        rate_limited_client.post("/auth/forgot-password", data={"email": "someone@example.com"})

    response = rate_limited_client.post("/auth/forgot-password", data={"email": "someone@example.com"})

    assert response.status_code == 429


def test_rate_limit_exceeded_shows_custom_error_page(rate_limited_client):
    for _ in range(10):
        rate_limited_client.post(
            "/auth/login", data={"email": "nobody@example.com", "password": "wrongpassword"}
        )

    response = rate_limited_client.post(
        "/auth/login", data={"email": "nobody@example.com", "password": "wrongpassword"}
    )

    assert b"Too Many Requests" in response.data