"""Tests for the admin stats dashboard."""

from datetime import datetime, timedelta, timezone

from app.models.queue import QueueEntry
from app.models.student import Student
from app.extensions import db
from tests.conftest import register, login


def _make_admin():
    admin = Student(full_name="Admin", email="admin@example.com", role="admin")
    admin.set_password("AdminPass123!")
    db.session.add(admin)
    db.session.commit()


def test_stats_requires_admin(client, db):
    register(client, email="student@example.com")
    login(client, email="student@example.com")

    response = client.get("/admin/stats")

    assert response.status_code == 403


def test_stats_shows_correct_total_students_and_active_queue(client, db, app):
    register(client, email="s1@example.com")
    login(client, email="s1@example.com")
    client.post("/student/queue/join", follow_redirects=True)
    client.get("/auth/logout")

    register(client, email="s2@example.com")
    login(client, email="s2@example.com")
    client.get("/auth/logout")

    with app.app_context():
        _make_admin()
    login(client, email="admin@example.com", password="AdminPass123!")

    response = client.get("/admin/stats")

    assert response.status_code == 200
    with app.app_context():
        assert Student.query.filter_by(role=Student.ROLE_STUDENT).count() == 2
        assert QueueEntry.query.filter_by(status=QueueEntry.STATUS_WAITING).count() == 1


def test_average_service_minutes_reflects_completed_history(app, db):
    with app.app_context():
        student = Student(full_name="History", email="history2@example.com")
        student.set_password("Password123!")
        db.session.add(student)
        db.session.commit()

        called_at = datetime.now(timezone.utc) - timedelta(minutes=20)
        entry = QueueEntry(
            token_number="Q-STATS-0001",
            student_id=student.id,
            status=QueueEntry.STATUS_COMPLETED,
            called_at=called_at,
            completed_at=called_at + timedelta(minutes=10),
        )
        db.session.add(entry)
        db.session.commit()

        assert QueueEntry.average_service_minutes() == 10.0