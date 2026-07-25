"""Tests for custom error pages and the error-handling setup."""

from tests.conftest import register, login


def test_404_renders_custom_page(client):
    response = client.get("/this-page-does-not-exist")

    assert response.status_code == 404
    assert b"Page Not Found" in response.data


def test_403_renders_custom_page_for_non_admin(client, db):
    register(client, email="student@example.com")
    login(client, email="student@example.com")

    response = client.get("/admin/dashboard")

    assert response.status_code == 403
    assert b"Access Denied" in response.data


def test_csrf_error_renders_custom_page(csrf_client, db):
    register(csrf_client, email="csrftest@example.com")
    login(csrf_client, email="csrftest@example.com")

    # Deliberately posting with no csrf_token field at all
    response = csrf_client.post("/student/queue/join")

    assert response.status_code == 400
    assert b"Bad Request" in response.data


def test_500_renders_custom_page(app, db):
    # Both flags are necessary: TESTING normally makes exceptions
    # propagate straight to the test itself (useful for debugging
    # your own tests), which would bypass the 500 handler entirely.
    # Turning both off here lets us verify the handler exactly as it
    # would behave for a real user hitting a real, unexpected error.
    app.config["TESTING"] = False
    app.config["PROPAGATE_EXCEPTIONS"] = False

    @app.route("/__force-error-for-test")
    def _force_error():
        raise RuntimeError("Intentional error, for testing the 500 handler only.")

    client = app.test_client()
    response = client.get("/__force-error-for-test")

    assert response.status_code == 500
    assert b"Something Went Wrong" in response.data