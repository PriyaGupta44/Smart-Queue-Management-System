import re

import pytest

from app import create_app
from app.extensions import db as _db


@pytest.fixture()
def app():
    application = create_app("testing")
    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db(app):
    return _db


@pytest.fixture()
def csrf_client(app):
    """A test client for an app with CSRF protection actually enabled.

    The plain `client` fixture uses TestingConfig, which disables CSRF
    so most tests can post forms without needing a real token. This
    fixture flips it back on for the tests that specifically need to
    verify CSRF is enforced.
    """
    app.config["WTF_CSRF_ENABLED"] = True
    return app.test_client()


def _csrf_token(client, get_url):
    """Fetch a page and pull its real CSRF token out of the rendered
    HTML, if one is present.

    Returns None when the page has no csrf_token field (e.g. CSRF is
    disabled for this app under the plain `client` fixture) — callers
    only attach the token to their POST when one was actually found,
    so this works transparently whether CSRF protection is on or off.
    """
    response = client.get(get_url)
    match = re.search(rb'name="csrf_token" value="([^"]+)"', response.data)
    return match.group(1).decode() if match else None


def register(client, email="student@example.com", password="password123", full_name="Test Student"):
    data = {
        "full_name": full_name,
        "email": email,
        "password": password,
        "confirm_password": password,
    }
    token = _csrf_token(client, "/auth/register")
    if token:
        data["csrf_token"] = token
    return client.post("/auth/register", data=data, follow_redirects=True)


def login(client, email="student@example.com", password="password123"):
    data = {"email": email, "password": password}
    token = _csrf_token(client, "/auth/login")
    if token:
        data["csrf_token"] = token
    return client.post("/auth/login", data=data, follow_redirects=True)


@pytest.fixture()
def rate_limited_client(app):
    """A test client with rate limiting actually enabled.

    Flask-Limiter only sets up its storage backend if RATELIMIT_ENABLED
    is True at the moment init_app() runs. Since the `app` fixture is
    built with RATELIMIT_ENABLED = False (TestingConfig), storage was
    never created — so we flip the config flag and call init_app()
    again here, which re-runs that setup now that it's enabled.
    """
    from app.extensions import limiter

    app.config["RATELIMIT_ENABLED"] = True
    limiter.init_app(app)
    limiter.reset()
    yield app.test_client()
    app.config["RATELIMIT_ENABLED"] = False
    limiter.enabled = False