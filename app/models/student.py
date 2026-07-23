from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy.orm import validates

from app.extensions import db


class Student(UserMixin, db.Model):
    """
    A registered user. UserMixin gives us is_authenticated,
    is_active, is_anonymous, and get_id() for free so Flask-Login
    can work with this class directly.

    Note: rather than a separate Admin table, this uses one `role`
    column ("student" or "admin"). One users table is simpler to
    query and secure than juggling two Flask-Login user classes,
    and your README's two roles map cleanly onto one flag.
    """

    __tablename__ = "students"

    # Single source of truth for valid role values. Referenced by the
    # validator below, by is_admin, and by seed_admin — nowhere else
    # in the codebase should the strings "student"/"admin" appear.
    ROLE_STUDENT = "student"
    ROLE_ADMIN = "admin"
    ALLOWED_ROLES = {ROLE_STUDENT, ROLE_ADMIN}

    __table_args__ = (
        # Defense in depth: even if a bug or a raw SQL script bypasses
        # the @validates hook below, SQLite itself will still refuse
        # to write a row with an invalid role. Keep this list in sync
        # with ALLOWED_ROLES above by hand — SQL CHECK constraints
        # can't reference Python constants directly.
        db.CheckConstraint("role IN ('student', 'admin')", name="ck_students_role_valid"),
    )

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=ROLE_STUDENT)  # "student" | "admin"
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # one student can have many queue tokens over time (retakes, repeat visits)
    queue_entries = db.relationship("QueueEntry", backref="student", lazy="dynamic")

    @validates("role")
    def validate_role(self, key, value):
        """Runs automatically whenever `role` is set — on __init__,
        and on any later `student.role = ...` assignment.

        Normalizes casing/whitespace, then rejects anything outside
        ALLOWED_ROLES with a clear error instead of letting a typo
        silently become "the role is now whatever string I typed"."""
        normalized = value.strip().lower()
        if normalized not in self.ALLOWED_ROLES:
            raise ValueError(
                f"Invalid role {value!r}. Must be one of {sorted(self.ALLOWED_ROLES)}."
            )
        return normalized

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    @property
    def is_admin(self):
        return self.role == self.ROLE_ADMIN

    def __repr__(self):
        return f"<Student {self.email}>"