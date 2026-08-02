"""Tests for token-called and password-changed email notifications."""

from app.models.queue import QueueEntry
from app.models.student import Student
from app.extensions import db, mail
from tests.conftest import register, login


def _make_admin():
    admin = Student(full_name="Admin", email="admin@example.com", role="admin")
    admin.set_password("AdminPass123!")
    db.session.add(admin)
    db.session.commit()


def test_calling_a_token_sends_notification_email(client, db, app):
    register(client, email="notifyme@example.com")
    login(client, email="notifyme@example.com")
    client.post("/student/queue/join", follow_redirects=True)
    client.get("/auth/logout")

    with app.app_context():
        _make_admin()
        entry = QueueEntry.query.first()
    login(client, email="admin@example.com", password="AdminPass123!")

    with mail.record_messages() as outbox:
        client.post(f"/admin/queue/{entry.id}/call", follow_redirects=True)

    assert len(outbox) == 1
    assert outbox[0].recipients == ["notifyme@example.com"]
    assert "called" in outbox[0].subject.lower()


def test_changing_password_sends_notification_email(client, db):
    register(client, email="pwnotify@example.com")
    login(client, email="pwnotify@example.com")

    with mail.record_messages() as outbox:
        client.post(
            "/student/profile/change-password",
            data={
                "current_password": "Password123!",
                "new_password": "BrandNew1!",
                "confirm_new_password": "BrandNew1!",
            },
            follow_redirects=True,
        )

    assert len(outbox) == 1
    assert outbox[0].recipients == ["pwnotify@example.com"]