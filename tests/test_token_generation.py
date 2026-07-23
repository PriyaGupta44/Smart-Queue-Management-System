"""
Tests for the token-number race condition fix.

Real concurrent requests are hard to test deterministically, so these
tests use monkeypatch to force a controlled collision instead of
relying on timing or actual threads.
"""

import app.student.routes as student_routes
from app.models.queue import QueueEntry
from tests.conftest import register, login


def test_join_queue_succeeds_normally(client, db, app):
    register(client, email="alice@example.com")
    login(client, email="alice@example.com")

    response = client.post("/student/queue/join", follow_redirects=True)

    assert response.status_code == 200
    with app.app_context():
        assert QueueEntry.query.count() == 1


def test_join_queue_retries_and_succeeds_after_one_collision(client, db, app, monkeypatch):
    register(client, email="first@example.com")
    login(client, email="first@example.com")

    colliding_token = "Q-20260101-1234"
    monkeypatch.setattr(student_routes, "_generate_token_number", lambda: colliding_token)
    client.post("/student/queue/join", follow_redirects=True)
    client.get("/auth/logout")

    # Second student: first attempt collides with the token above,
    # second attempt gets a fresh, unique one.
    attempts = iter([colliding_token, "Q-20260101-5678"])
    monkeypatch.setattr(student_routes, "_generate_token_number", lambda: next(attempts))

    register(client, email="second@example.com")
    login(client, email="second@example.com")
    response = client.post("/student/queue/join", follow_redirects=True)

    assert response.status_code == 200
    assert b"Joined the queue" in response.data
    with app.app_context():
        tokens = [e.token_number for e in QueueEntry.query.all()]
        assert tokens.count(colliding_token) == 1  # no duplicate was ever committed
        assert "Q-20260101-5678" in tokens


def test_join_queue_fails_gracefully_when_every_retry_collides(client, db, app, monkeypatch):
    register(client, email="first@example.com")
    login(client, email="first@example.com")

    colliding_token = "Q-20260101-9999"
    monkeypatch.setattr(student_routes, "_generate_token_number", lambda: colliding_token)
    client.post("/student/queue/join", follow_redirects=True)
    client.get("/auth/logout")

    # Second student's generator always returns the same, already-taken
    # token — every one of the 5 retry attempts should collide.
    register(client, email="second@example.com")
    login(client, email="second@example.com")
    response = client.post("/student/queue/join", follow_redirects=True)

    assert response.status_code == 200  # graceful redirect, not a 500
    assert b"couldn't generate a queue token" in response.data
    with app.app_context():
        # Only the first student's entry exists — the second student's
        # join attempt never committed a (duplicate) row.
        assert QueueEntry.query.count() == 1