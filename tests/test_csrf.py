"""
Regression tests for CSRF protection.

The shared `client` fixture (see conftest.py) uses TestingConfig, which
sets WTF_CSRF_ENABLED = False so the rest of the suite can POST forms
without needing a real token. That's convenient, but it also means the
main suite would stay green even if every form's CSRF token silently
broke or got removed - which is exactly what happened before Day 11.

These tests use a separate fixture that flips CSRF back on, so we
actually verify the protection is doing its job.
"""

import re

import pytest

from tests.conftest import register, login


@pytest.fixture()
def csrf_client(app):
    """A test client for an app with CSRF protection actually enabled."""
    app.config["WTF_CSRF_ENABLED"] = True
    return app.test_client()


def _extract_csrf_token(html: bytes) -> str:
    """Pull the real csrf_token value out of a rendered page's HTML."""
    match = re.search(rb'name="csrf_token" value="([^"]+)"', html)
    assert match is not None, "No CSRF token field found in the page"
    return match.group(1).decode()


def test_join_queue_rejected_without_csrf_token(csrf_client):
    """A POST with no csrf_token field must be rejected (400)."""
    register(csrf_client)
    login(csrf_client)

    response = csrf_client.post("/student/queue/join")

    assert response.status_code == 400


def test_join_queue_succeeds_with_real_csrf_token(csrf_client):
    """A POST carrying the token the page actually rendered must succeed."""
    register(csrf_client)
    login(csrf_client)

    dashboard_page = csrf_client.get("/student/dashboard")
    token = _extract_csrf_token(dashboard_page.data)

    response = csrf_client.post(
        "/student/queue/join",
        data={"csrf_token": token},
        follow_redirects=True,
    )

    assert response.status_code == 200


def test_admin_call_next_rejected_without_csrf_token(csrf_client, db, app):
    """The admin call-next action must also enforce CSRF."""
    from app.models.student import Student
    from app.models.queue import QueueEntry

    register(csrf_client, email="applicant@example.com")
    login(csrf_client, email="applicant@example.com")
    csrf_client.post(
        "/student/queue/join",
        data={"csrf_token": _extract_csrf_token(
            csrf_client.get("/student/dashboard").data
        )},
        follow_redirects=True,
    )
    csrf_client.get("/auth/logout")

    with app.app_context():
        admin = Student(full_name="Admin", email="admin@example.com", role="admin")
        admin.set_password("adminpass123")
        db.session.add(admin)
        db.session.commit()

    login(csrf_client, email="admin@example.com", password="adminpass123")

    entry = QueueEntry.query.first()
    response = csrf_client.post(f"/admin/queue/{entry.id}/call")

    assert response.status_code == 400