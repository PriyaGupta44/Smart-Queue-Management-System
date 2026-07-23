"""
Tests for Student.role validation — both the Python-level @validates
hook and the database-level CHECK constraint.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.models.student import Student


def _new_student(**overrides):
    defaults = dict(full_name="Test Student", email="test@example.com")
    defaults.update(overrides)
    student = Student(**defaults)
    student.set_password("password123")
    return student


def test_default_role_is_student(app):
    with app.app_context():
        student = _new_student()
        assert student.role == Student.ROLE_STUDENT
        assert student.is_admin is False


def test_role_rejects_invalid_value(app):
    with app.app_context():
        with pytest.raises(ValueError):
            _new_student(role="superadmin")


def test_role_normalizes_case_and_whitespace(app):
    with app.app_context():
        student = _new_student(role="  ADMIN  ")
        assert student.role == Student.ROLE_ADMIN
        assert student.is_admin is True


def test_role_check_constraint_enforced_at_database_level(app, db):
    """Even code that bypasses the ORM entirely (raw SQL) should be
    blocked by the database's own CHECK constraint."""
    with app.app_context():
        with pytest.raises(IntegrityError):
            db.session.execute(
                text(
                    "INSERT INTO students (full_name, email, password_hash, role) "
                    "VALUES ('Hacker', 'hacker@example.com', 'x', 'superadmin')"
                )
            )
            db.session.commit()
        db.session.rollback()