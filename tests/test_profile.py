"""Tests for profile editing and change-password."""

from app.models.student import Student
from tests.conftest import register, login


def test_profile_update_changes_full_name(client, db, app):
    register(client, email="profileuser@example.com", full_name="Old Name")
    login(client, email="profileuser@example.com")

    response = client.post("/student/profile", data={"full_name": "New Name"}, follow_redirects=True)

    assert response.status_code == 200
    with app.app_context():
        student = Student.query.filter_by(email="profileuser@example.com").first()
        assert student.full_name == "New Name"


def test_change_password_requires_correct_current_password(client, db):
    register(client, email="pwuser@example.com")
    login(client, email="pwuser@example.com")

    response = client.post(
        "/student/profile/change-password",
        data={
            "current_password": "WrongPassword1!",
            "new_password": "BrandNew1!",
            "confirm_new_password": "BrandNew1!",
        },
        follow_redirects=True,
    )

    assert b"Current password is incorrect" in response.data


def test_change_password_succeeds_with_correct_current_password(client, db, app):
    register(client, email="pwuser2@example.com")
    login(client, email="pwuser2@example.com")

    client.post(
        "/student/profile/change-password",
        data={
            "current_password": "Password123!",
            "new_password": "BrandNew1!",
            "confirm_new_password": "BrandNew1!",
        },
        follow_redirects=True,
    )

    with app.app_context():
        student = Student.query.filter_by(email="pwuser2@example.com").first()
        assert student.check_password("BrandNew1!")