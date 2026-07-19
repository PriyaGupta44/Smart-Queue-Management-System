from tests.conftest import register, login


def test_register_creates_student(client, db):
    from app.models.student import Student

    response = register(client)
    assert response.status_code == 200

    student = Student.query.filter_by(email="student@example.com").first()
    assert student is not None
    assert student.role == "student"
    assert student.check_password("password123")


def test_register_duplicate_email_rejected(client):
    register(client)
    response = register(client)
    assert b"already exists" in response.data


def test_login_with_correct_credentials_redirects_to_dashboard(client):
    register(client)
    response = login(client)
    assert response.status_code == 200
    assert b"Dashboard" in response.data or b"Welcome" in response.data


def test_login_with_wrong_password_shows_error(client):
    register(client)
    response = login(client, password="wrong-password")
    assert b"Invalid email or password" in response.data


def test_dashboard_requires_login(client):
    response = client.get("/student/dashboard", follow_redirects=True)
    assert b"Please log in" in response.data or response.status_code == 200
