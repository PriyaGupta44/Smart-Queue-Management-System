"""Tests for student self-cancel and admin skip/recall."""

from app.models.queue import QueueEntry
from app.models.student import Student
from app.extensions import db
from tests.conftest import register, login


def _make_admin():
    admin = Student(full_name="Admin", email="admin@example.com", role="admin")
    admin.set_password("AdminPass123!")
    db.session.add(admin)
    db.session.commit()


def test_student_can_cancel_own_waiting_token(client, db, app):
    register(client, email="canceller@example.com")
    login(client, email="canceller@example.com")
    client.post("/student/queue/join", follow_redirects=True)

    client.post("/student/queue/cancel", follow_redirects=True)

    with app.app_context():
        entry = QueueEntry.query.first()
        assert entry.status == QueueEntry.STATUS_CANCELLED


def test_admin_skip_requires_called_status(client, db, app):
    register(client, email="skiptest@example.com")
    login(client, email="skiptest@example.com")
    client.post("/student/queue/join", follow_redirects=True)
    client.get("/auth/logout")

    with app.app_context():
        _make_admin()
        entry = QueueEntry.query.first()
    login(client, email="admin@example.com", password="AdminPass123!")

    response = client.post(f"/admin/queue/{entry.id}/skip", follow_redirects=True)

    assert b"must be called before" in response.data
    with app.app_context():
        assert db.session.get(QueueEntry, entry.id).status == QueueEntry.STATUS_WAITING


def test_admin_can_skip_and_recall_a_called_entry(client, db, app):
    register(client, email="recalltest@example.com")
    login(client, email="recalltest@example.com")
    client.post("/student/queue/join", follow_redirects=True)
    client.get("/auth/logout")

    with app.app_context():
        _make_admin()
        entry = QueueEntry.query.first()
    login(client, email="admin@example.com", password="AdminPass123!")

    client.post(f"/admin/queue/{entry.id}/call", follow_redirects=True)
    client.post(f"/admin/queue/{entry.id}/skip", follow_redirects=True)
    with app.app_context():
        assert db.session.get(QueueEntry, entry.id).status == QueueEntry.STATUS_SKIPPED

    client.post(f"/admin/queue/{entry.id}/recall", follow_redirects=True)
    with app.app_context():
        assert db.session.get(QueueEntry, entry.id).status == QueueEntry.STATUS_CALLED