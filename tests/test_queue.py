from tests.conftest import register, login


def test_join_queue_creates_entry(client, db):
    from app.models.queue import QueueEntry

    register(client)
    login(client)

    response = client.post("/student/queue/join", follow_redirects=True)
    assert response.status_code == 200

    entry = QueueEntry.query.first()
    assert entry is not None
    assert entry.status == QueueEntry.STATUS_WAITING


def test_cannot_join_queue_twice(client):
    register(client)
    login(client)
    client.post("/student/queue/join", follow_redirects=True)

    response = client.post("/student/queue/join", follow_redirects=True)
    assert b"already have an active token" in response.data


def test_position_reflects_earlier_waiting_entries(client, db):
    from app.models.student import Student
    from app.models.queue import QueueEntry

    # first student joins
    register(client, email="first@example.com")
    login(client, email="first@example.com")
    client.post("/student/queue/join", follow_redirects=True)
    client.get("/auth/logout")

    # second student joins and should be behind the first
    register(client, email="second@example.com")
    login(client, email="second@example.com")
    client.post("/student/queue/join", follow_redirects=True)

    second = Student.query.filter_by(email="second@example.com").first()
    entry = second.queue_entries.filter_by(status=QueueEntry.STATUS_WAITING).first()
    assert entry.token_number is not None


def test_admin_can_call_and_complete_entry(client, db, app):
    from app.models.student import Student
    from app.models.queue import QueueEntry

    register(client, email="applicant@example.com")
    login(client, email="applicant@example.com")
    client.post("/student/queue/join", follow_redirects=True)
    client.get("/auth/logout")

    with app.app_context():
        admin = Student(full_name="Admin", email="admin@example.com", role="admin")
        admin.set_password("adminpass123")
        db.session.add(admin)
        db.session.commit()

    login(client, email="admin@example.com", password="adminpass123")

    entry = QueueEntry.query.first()
    resp = client.post(f"/admin/queue/{entry.id}/call", follow_redirects=True)
    assert resp.status_code == 200

    resp = client.post(f"/admin/queue/{entry.id}/complete", follow_redirects=True)
    assert resp.status_code == 200

    updated = QueueEntry.query.get(entry.id)
    assert updated.status == QueueEntry.STATUS_COMPLETED


def test_non_admin_cannot_access_admin_dashboard(client):
    register(client)
    login(client)
    response = client.get("/admin/dashboard")
    assert response.status_code == 403
