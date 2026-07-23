"""Tests for the forgot-password / reset-password flow."""

from app.extensions import db
from app.models.student import Student


def _make_student(email="reset@example.com", password="oldpassword123"):
    student = Student(full_name="Reset Test", email=email)
    student.set_password(password)
    db.session.add(student)
    db.session.commit()
    return student


def test_forgot_password_shows_generic_message_for_unknown_email(client, app):
    with app.app_context():
        pass  # no student created — this email genuinely doesn't exist

    response = client.post(
        "/auth/forgot-password",
        data={"email": "nobody@example.com"},
        follow_redirects=True,
    )

    assert b"If an account with that email exists" in response.data


def test_forgot_password_shows_identical_message_for_known_email(client, app, db):
    with app.app_context():
        _make_student()

    response = client.post(
        "/auth/forgot-password",
        data={"email": "reset@example.com"},
        follow_redirects=True,
    )

    # Same wording as the "unknown email" case above — that's the point.
    assert b"If an account with that email exists" in response.data


def test_reset_password_with_valid_token_changes_password(client, app, db):
    with app.app_context():
        student = _make_student()
        token = student.get_reset_token()

    response = client.post(
        f"/auth/reset-password/{token}",
        data={"password": "newpassword456", "confirm_password": "newpassword456"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    with app.app_context():
        updated = Student.query.filter_by(email="reset@example.com").first()
        assert updated.check_password("newpassword456")
        assert not updated.check_password("oldpassword123")


def test_reset_password_with_invalid_token_redirects_to_forgot_password(client):
    response = client.get("/auth/reset-password/not-a-real-token", follow_redirects=True)

    assert b"invalid or has expired" in response.data


def test_verify_reset_token_rejects_expired_token(app, db):
    with app.app_context():
        student = _make_student()
        token = student.get_reset_token()

        # max_age=-1 guarantees the token is treated as already expired,
        # regardless of how fast this test runs.
        result = Student.verify_reset_token(token, max_age=-1)

        assert result is None


def test_verify_reset_token_accepts_valid_token(app, db):
    with app.app_context():
        student = _make_student()
        token = student.get_reset_token()

        result = Student.verify_reset_token(token)

        assert result is not None
        assert result.email == student.email