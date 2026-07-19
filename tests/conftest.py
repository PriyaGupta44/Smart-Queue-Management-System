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


def register(client, email="student@example.com", password="password123", full_name="Test Student"):
    return client.post(
        "/auth/register",
        data={
            "full_name": full_name,
            "email": email,
            "password": password,
            "confirm_password": password,
        },
        follow_redirects=True,
    )


def login(client, email="student@example.com", password="password123"):
    return client.post(
        "/auth/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    )
