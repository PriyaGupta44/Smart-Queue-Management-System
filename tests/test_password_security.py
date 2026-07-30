"""Tests for password strength validation and account lockout."""

from app.models.student import Student
from tests.conftest import register, login


def test_register_rejects_password_without_uppercase(client, db):
    response = client.post(
        "/auth/register",
        data={
            "full_name": "Test User",
            "email": "weak1@example.com",
            "password": "lowercase1!",
            "confirm_password": "lowercase1!",
        },
    )
    assert b"uppercase" in response.data.lower()


def test_register_rejects_password_without_special_character(client, db):
    response = client.post(
        "/auth/register",
        data={
            "full_name": "Test User",
            "email": "weak2@example.com",
            "password": "Password1",
            "confirm_password": "Password1",
        },
    )
    assert b"special character" in response.data.lower()


def test_register_accepts_strong_password(client, db, app):
    register(client, email="strong@example.com", password="Str0ng!Pass")

    with app.app_context():
        assert Student.query.filter_by(email="strong@example.com").first() is not None


def test_login_locks_account_after_max_failed_attempts(client, db, app):
    register(client, email="locktest@example.com")
    client.get("/auth/logout")

    for _ in range(5):
        client.post("/auth/login", data={"email": "locktest@example.com", "password": "wrongpassword"})

    with app.app_context():
        student = Student.query.filter_by(email="locktest@example.com").first()
        assert student.is_locked()


def test_locked_account_rejects_even_correct_password(client, db, app):
    register(client, email="locktest2@example.com")
    client.get("/auth/logout")

    for _ in range(5):
        client.post("/auth/login", data={"email": "locktest2@example.com", "password": "wrongpassword"})

    response = client.post(
        "/auth/login",
        data={"email": "locktest2@example.com", "password": "Password123!"},
        follow_redirects=True,
    )
    assert b"temporarily locked" in response.data


def test_successful_login_resets_failed_attempts(client, db, app):
    register(client, email="resettest@example.com")
    client.get("/auth/logout")

    client.post("/auth/login", data={"email": "resettest@example.com", "password": "wrongpassword"})
    client.post(
        "/auth/login",
        data={"email": "resettest@example.com", "password": "Password123!"},
        follow_redirects=True,
    )

    with app.app_context():
        student = Student.query.filter_by(email="resettest@example.com").first()
        assert student.failed_login_attempts == 0