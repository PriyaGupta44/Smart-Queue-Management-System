from datetime import datetime, timedelta, timezone
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
    failed_login_attempts = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    locked_until = db.Column(db.DateTime, nullable=True)
    avatar_filename = db.Column(db.String(255), nullable=True)
    last_login_at = db.Column(db.DateTime, nullable=True)


    def __init__(self, **kwargs):
        """Apply the role default immediately, in Python.

        db.Column(default=...) is a DATABASE-level default — SQLAlchemy
        only applies it when the row is flushed/committed, not the
        moment Student(...) is constructed. Without this override, a
        freshly-built, not-yet-saved Student has role=None, which is
        surprising and fragile to test against. Setting it here also
        means @validates("role") runs immediately, so the value is
        normalized from the moment the object exists, not just after
        a database round-trip.
        """
        kwargs.setdefault("role", self.ROLE_STUDENT)
        super().__init__(**kwargs)

    @validates("role")
    def validate_role(self, key, value):
        ...

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

    
    MAX_FAILED_LOGIN_ATTEMPTS = 5
    LOCKOUT_DURATION_MINUTES = 15

    def is_locked(self):
        if self.locked_until is None:
            return False
        locked_until = self.locked_until

        if locked_until.tzinfo is None:
            # SQLite strips timezone info on round-trip — we always
            # store this as UTC, so it's safe to reattach it here
            # before comparing against a timezone-aware "now".
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        return locked_until > datetime.now(timezone.utc)

    def register_failed_login(self):
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= self.MAX_FAILED_LOGIN_ATTEMPTS:
            self.locked_until = datetime.now(timezone.utc) + timedelta(minutes=self.LOCKOUT_DURATION_MINUTES)

    def register_successful_login(self):
        self.failed_login_attempts = 0
        self.locked_until = None

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