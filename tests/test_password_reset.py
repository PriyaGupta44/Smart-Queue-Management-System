"""Tests for the forgot-password / reset-password flow."""

from app.extensions import db, mail
from app.models.student import Student


def _make_student(email="reset@example.com", password="oldpassword123"):
    student = Student(full_name="Reset Test", email=email)
    student.set_password(password)
    db.session.add(student)
    db.session.commit()
    return student


def test_forgot_password_shows_generic_message_for_unknown_email(client, app):
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

    assert b"If an account with that email exists" in response.data


def test_forgot_password_sends_email_for_known_account(client, app, db):
    with app.app_context():
        _make_student()

    with mail.record_messages() as outbox:
        client.post(
            "/auth/forgot-password",
            data={"email": "reset@example.com"},
            follow_redirects=True,
        )

    assert len(outbox) == 1
    assert outbox[0].recipients == ["reset@example.com"]
    assert "reset your" in outbox[0].subject.lower()
    assert "reset-password" in outbox[0].body


def test_forgot_password_sends_no_email_for_unknown_account(client, app):
    with mail.record_messages() as outbox:
        client.post(
            "/auth/forgot-password",
            data={"email": "nobody@example.com"},
            follow_redirects=True,
        )

    assert len(outbox) == 0


def test_reset_password_with_valid_token_changes_password(client, app, db):
    with app.app_context():
        student = _make_student()
        token = student.get_reset_token()

    response = client.post(
        f"/auth/reset-password/{token}",
        data={"password": "NewPass456!", "confirm_password": "NewPass456!"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    with app.app_context():
        updated = Student.query.filter_by(email="reset@example.com").first()
        assert updated.check_password("NewPass456!")
        assert not updated.check_password("oldpassword123")


def test_reset_password_with_invalid_token_redirects_to_forgot_password(client):
    response = client.get("/auth/reset-password/not-a-real-token", follow_redirects=True)

    assert b"invalid or has expired" in response.data


def test_verify_reset_token_rejects_expired_token(app, db):
    with app.app_context():
        student = _make_student()
        token = student.get_reset_token()

        result = Student.verify_reset_token(token, max_age=-1)

        assert result is None


def test_verify_reset_token_accepts_valid_token(app, db):
    with app.app_context():
        student = _make_student()
        token = student.get_reset_token()

        result = Student.verify_reset_token(token)

        assert result is not None
        assert result.email == student.email