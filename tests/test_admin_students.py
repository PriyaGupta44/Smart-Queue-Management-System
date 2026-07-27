"""Tests for the admin student list and per-student detail view."""

from app.models.student import Student
from app.extensions import db
from tests.conftest import register, login


def _make_admin():
    admin = Student(full_name="Admin", email="admin@example.com", role="admin")
    admin.set_password("adminpass123")
    db.session.add(admin)
    db.session.commit()


def _login_as_admin(client):
    return login(client, email="admin@example.com", password="adminpass123")


def test_students_list_requires_admin(client, db, app):
    register(client, email="student@example.com")
    login(client, email="student@example.com")

    response = client.get("/admin/students")

    assert response.status_code == 403


def test_students_list_shows_registered_students(client, db, app):
    register(client, email="alice@example.com", full_name="Alice Johnson")
    client.get("/auth/logout")
    with app.app_context():
        _make_admin()
    _login_as_admin(client)

    response = client.get("/admin/students")

    assert response.status_code == 200
    assert b"Alice Johnson" in response.data


def test_students_list_excludes_admin_accounts(client, db, app):
    with app.app_context():
        _make_admin()
    _login_as_admin(client)

    response = client.get("/admin/students")

    assert b"admin@example.com" not in response.data


def test_students_list_search_filters_by_name(client, db, app):
    register(client, email="alice@example.com", full_name="Alice Johnson")
    client.get("/auth/logout")
    register(client, email="bob@example.com", full_name="Bob Smith")
    client.get("/auth/logout")
    with app.app_context():
        _make_admin()
    _login_as_admin(client)

    response = client.get("/admin/students?q=Alice")

    assert b"Alice Johnson" in response.data
    assert b"Bob Smith" not in response.data


def test_student_detail_shows_queue_history(client, db, app):
    register(client, email="alice@example.com", full_name="Alice Johnson")
    login(client, email="alice@example.com")
    client.post("/student/queue/join", follow_redirects=True)
    client.get("/auth/logout")

    with app.app_context():
        _make_admin()
        student_id = Student.query.filter_by(email="alice@example.com").first().id
    _login_as_admin(client)

    response = client.get(f"/admin/students/{student_id}")

    assert response.status_code == 200
    assert b"Alice Johnson" in response.data
    assert b"waiting" in response.data.lower()


def test_student_detail_requires_admin(client, db, app):
    register(client, email="alice@example.com")
    with app.app_context():
        student_id = Student.query.filter_by(email="alice@example.com").first().id
    client.get("/auth/logout")

    register(client, email="intruder@example.com")
    login(client, email="intruder@example.com")

    response = client.get(f"/admin/students/{student_id}")

    assert response.status_code == 403