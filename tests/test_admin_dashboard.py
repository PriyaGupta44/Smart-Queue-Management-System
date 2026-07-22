"""
Tests for the admin dashboard's search and pagination.

Split out from test_queue.py on purpose — the Day 9 review noted
admin-specific coverage was buried inside the queue test file, and
this is a natural point to fix that as admin coverage grows.
"""

from tests.conftest import register, login


def _make_admin(db, app):
    from app.models.student import Student

    with app.app_context():
        admin = Student(full_name="Admin", email="admin@example.com", role="admin")
        admin.set_password("adminpass123")
        db.session.add(admin)
        db.session.commit()


def _login_as_admin(client):
    return login(client, email="admin@example.com", password="adminpass123")


def _join_queue_as(client, email, full_name):
    register(client, email=email, full_name=full_name)
    login(client, email=email)
    client.post("/student/queue/join", follow_redirects=True)
    client.get("/auth/logout")


def test_dashboard_search_filters_by_student_name(client, db, app):
    _join_queue_as(client, "alice@example.com", "Alice Johnson")
    _join_queue_as(client, "bob@example.com", "Bob Smith")
    _make_admin(db, app)
    _login_as_admin(client)

    response = client.get("/admin/dashboard?q=Alice")

    assert b"Alice Johnson" in response.data
    assert b"Bob Smith" not in response.data


def test_dashboard_search_with_no_matches_shows_empty_state(client, db, app):
    _join_queue_as(client, "alice@example.com", "Alice Johnson")
    _make_admin(db, app)
    _login_as_admin(client)

    response = client.get("/admin/dashboard?q=nonexistentname")

    assert b"No matches found." in response.data


def test_dashboard_paginates_waiting_entries(client, db, app):
    for i in range(12):
        _join_queue_as(client, f"student{i}@example.com", f"Student {i}")
    _make_admin(db, app)
    _login_as_admin(client)

    page_one = client.get("/admin/dashboard")
    page_two = client.get("/admin/dashboard?waiting_page=2")

    assert page_one.data.count(b'class="btn-sm btn-call"') == 10
    assert page_two.data.count(b'class="btn-sm btn-call"') == 2


def test_dashboard_shows_correct_total_count_across_pages(client, db, app):
    for i in range(12):
        _join_queue_as(client, f"student{i}@example.com", f"Student {i}")
    _make_admin(db, app)
    _login_as_admin(client)

    response = client.get("/admin/dashboard")

    assert b"Waiting (12)" in response.data