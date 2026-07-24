"""Tests for the simulated payment flow and its confirmation message."""

from app.models.queue import QueueEntry
from tests.conftest import register, login


def test_pay_shows_congratulations_message_with_receipt(client, db, app):
    register(client, email="payer@example.com")
    login(client, email="payer@example.com")
    client.post("/student/queue/join", follow_redirects=True)

    with app.app_context():
        entry = QueueEntry.query.first()

    response = client.post(f"/student/payment/{entry.id}/pay", follow_redirects=True)

    assert response.status_code == 200
    assert "Congratulations".encode() in response.data
    assert entry.token_number.encode() in response.data


def test_paying_twice_does_not_repeat_congratulations_message(client, db, app):
    register(client, email="payer2@example.com")
    login(client, email="payer2@example.com")
    client.post("/student/queue/join", follow_redirects=True)

    with app.app_context():
        entry = QueueEntry.query.first()

    client.post(f"/student/payment/{entry.id}/pay", follow_redirects=True)
    response = client.post(f"/student/payment/{entry.id}/pay", follow_redirects=True)

    assert b"already been paid for" in response.data