from datetime import datetime, timezone
from flask import current_app
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
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

    ROLE_STUDENT = "student"
    ROLE_ADMIN = "admin"
    ALLOWED_ROLES = {ROLE_STUDENT, ROLE_ADMIN}

    __table_args__ = (
        db.CheckConstraint("role IN ('student', 'admin')", name="ck_students_role_valid"),
    )

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=ROLE_STUDENT)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    queue_entries = db.relationship("QueueEntry", backref="student", lazy="dynamic")

    @validates("role")
    def validate_role(self, key, value):
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

    def get_reset_token(self):
        """Build a signed, self-expiring token identifying this student.

        The token embeds this student's email plus a timestamp, both
        signed with the app's SECRET_KEY. Expiry isn't checked here —
        it's checked later in verify_reset_token(), which is the only
        place that knows how much time should be allowed to pass.
        """
        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        return serializer.dumps(self.email, salt="password-reset")

    @staticmethod
    def verify_reset_token(token, max_age=1800):
        """Validate a reset token and return the matching Student, or
        None if the token is invalid, tampered with, or expired.

        max_age is in seconds; 1800 = 30 minutes. Any failure here
        (bad signature, expired, unknown email) returns None rather
        than raising — callers shouldn't need to know *why* a token
        failed, just that it did.
        """
        serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        try:
            email = serializer.loads(token, salt="password-reset", max_age=max_age)
        except (BadSignature, SignatureExpired):
            return None
        return Student.query.filter_by(email=email).first()

    def __repr__(self):
        return f"<Student {self.email}>"