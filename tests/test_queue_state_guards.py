"""Tests for status-transition guards on admin call_next/complete."""

from app.models.queue import QueueEntry
from app.models.student import Student
from app.extensions import db
from tests.conftest import register, login


def _make_admin():
    admin = Student(full_name="Admin", email="admin@example.com", role="admin")
    admin.set_password("adminpass123")
    db.session.add(admin)
    db.session.commit()


def _join_queue_as(client, email):
    register(client, email=email)
    login(client, email=email)
    client.post("/student/queue/join", follow_redirects=True)
    client.get("/auth/logout")


def test_call_next_rejects_an_entry_that_is_not_waiting(client, db, app):
    _join_queue_as(client, "student1@example.com")
    with app.app_context():
        _make_admin()
    login(client, email="admin@example.com", password="adminpass123")

    with app.app_context():
        entry = QueueEntry.query.first()

    client.post(f"/admin/queue/{entry.id}/call", follow_redirects=True)  # now CALLED
    response = client.post(f"/admin/queue/{entry.id}/call", follow_redirects=True)  # calling again

    assert b"cannot be called" in response.data
    with app.app_context():
        refreshed = db.session.get(QueueEntry, entry.id)
        assert refreshed.status == QueueEntry.STATUS_CALLED  # unchanged, not corrupted


def test_complete_rejects_an_entry_that_has_not_been_called(client, db, app):
    _join_queue_as(client, "student2@example.com")
    with app.app_context():
        _make_admin()
    login(client, email="admin@example.com", password="adminpass123")

    with app.app_context():
        entry = QueueEntry.query.first()

    response = client.post(f"/admin/queue/{entry.id}/complete", follow_redirects=True)

    assert b"must be called before" in response.data
    with app.app_context():
        refreshed = db.session.get(QueueEntry, entry.id)
        assert refreshed.status == QueueEntry.STATUS_WAITING  