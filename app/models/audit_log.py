from datetime import datetime, timezone
from app.extensions import db


class AuditLog(db.Model):
    """Records administrative actions for accountability — who did
    what, and when. Deliberately append-only: nothing in the app
    ever edits or deletes an existing row."""

    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    target_type = db.Column(db.String(50), nullable=False)
    target_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    admin = db.relationship("Student", foreign_keys=[admin_id])

    def __repr__(self):
        return f"<AuditLog {self.action} on {self.target_type}:{self.target_id}>"