"""Tests for the queue-status JSON endpoint and the real-history ETA."""

from datetime import datetime, timedelta, timezone

from app.models.queue import QueueEntry
from app.models.student import Student
from app.extensions import db
from app.student.routes import _average_minutes_per_token
from tests.conftest import register, login


def test_queue_status_data_returns_inactive_for_student_with_no_entry(client, db, app):
    register(client, email="idle@example.com")
    login(client, email="idle@example.com")

    response = client.get("/student/queue/status/data")

    assert response.status_code == 200
    assert response.get_json()["active"] is False


def test_queue_status_data_returns_position_and_eta_for_waiting_entry(client, db, app):
    register(client, email="waiter@example.com")
    login(client, email="waiter@example.com")
    client.post("/student/queue/join", follow_redirects=True)

    response = client.get("/student/queue/status/data")
    data = response.get_json()

    assert data["active"] is True
    assert data["status"] == "waiting"
    assert data["position"] == 1
    assert data["eta_minutes"] is not None


def test_average_minutes_per_token_defaults_without_history(app, db):
    with app.app_context():
        assert _average_minutes_per_token() == 5.0


def test_average_minutes_per_token_reflects_recent_completed_entries(app, db):
    with app.app_context():
        student = Student(full_name="History Student", email="history@example.com")
        student.set_password("password123")
        db.session.add(student)
        db.session.commit()

        called_at = datetime.now(timezone.utc) - timedelta(minutes=10)
        completed_at = called_at + timedelta(minutes=8)  # actually took 8 minutes to serve

        entry = QueueEntry(
            token_number="Q-TEST-0001",
            student_id=student.id,
            status=QueueEntry.STATUS_COMPLETED,
            called_at=called_at,
            completed_at=completed_at,
        )
        db.session.add(entry)
        db.session.commit()

        assert _average_minutes_per_token() == 8.0