"""
Regression tests for the Blueprint template-resolution bug: admin and
student dashboards both used a bare "dashboard.html", so Flask
resolved whichever Blueprint's template folder happened to be
registered first — silently showing admins the student UI.
"""

from app.models.student import Student
from app.extensions import db
from tests.conftest import register, login


def _make_admin():
    admin = Student(full_name="Admin", email="admin@example.com", role="admin")
    admin.set_password("adminpass123")
    db.session.add(admin)
    db.session.commit()


def test_admin_dashboard_renders_admin_template_not_student(client, app, db):
    with app.app_context():
        _make_admin()

    login(client, email="admin@example.com", password="adminpass123")
    response = client.get("/admin/dashboard")

    # Markup that only exists in admin/dashboard.html
    assert b"Admin Dashboard" in response.data
    assert b'name="q"' in response.data  # the search box added on Day 12
    # Markup that only exists in student/dashboard.html — must NOT appear
    assert b"Join Queue" not in response.data


def test_student_dashboard_renders_student_template_not_admin(client, app, db):
    register(client, email="student@example.com")
    login(client, email="student@example.com")

    response = client.get("/student/dashboard")

    # Markup that only exists in student/dashboard.html
    assert b"Welcome," in response.data
    # Markup that only exists in admin/dashboard.html — must NOT appear
    assert b"Admin Dashboard" not in response.data
    assert b"Call Next" not in response.data