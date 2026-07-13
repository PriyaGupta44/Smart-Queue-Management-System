from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

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

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student")  # "student" | "admin"
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # one student can have many queue tokens over time (retakes, repeat visits)
    queue_entries = db.relationship("QueueEntry", backref="student", lazy="dynamic")

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    @property
    def is_admin(self):
        return self.role == "admin"

    def __repr__(self):
        return f"<Student {self.email}>"