"""Tests for the student payment history and receipt views."""

from app.models.queue import QueueEntry
from app.models.payment import Payment
from tests.conftest import register, login


def _join_and_pay(client, app, email):
    register(client, email=email)
    login(client, email=email)
    client.post("/student/queue/join", follow_redirects=True)
    with app.app_context():
        entry = QueueEntry.query.filter_by(token_number=QueueEntry.query.first().token_number).first()
    client.post(f"/student/payment/{entry.id}/pay", follow_redirects=True)
    with app.app_context():
        payment = Payment.query.order_by(Payment.id.desc()).first()
    return payment


def test_payment_history_shows_own_payment(client, db, app):
    payment = _join_and_pay(client, app, "payer@example.com")

    response = client.get("/student/payments")

    assert response.status_code == 200
    assert payment.receipt_number.encode() in response.data


def test_payment_history_empty_state_for_student_with_no_payments(client, db, app):
    register(client, email="newbie@example.com")
    login(client, email="newbie@example.com")

    response = client.get("/student/payments")

    assert b"have not made any payments" in response.data


def test_receipt_view_shows_own_receipt(client, db, app):
    payment = _join_and_pay(client, app, "receiptowner@example.com")

    response = client.get(f"/student/payments/{payment.id}/receipt")

    assert response.status_code == 200
    assert payment.receipt_number.encode() in response.data


def test_receipt_view_returns_404_for_another_students_receipt(client, db, app):
    payment = _join_and_pay(client, app, "ownerA@example.com")
    client.get("/auth/logout")

    register(client, email="intruderB@example.com")
    login(client, email="intruderB@example.com")

    response = client.get(f"/student/payments/{payment.id}/receipt")

    assert response.status_code == 404


def test_payment_history_does_not_leak_other_students_receipts(client, db, app):
    other_payment = _join_and_pay(client, app, "ownerC@example.com")
    client.get("/auth/logout")

    register(client, email="viewerD@example.com")
    login(client, email="viewerD@example.com")

    response = client.get("/student/payments")

    assert other_payment.receipt_number.encode() not in response.data