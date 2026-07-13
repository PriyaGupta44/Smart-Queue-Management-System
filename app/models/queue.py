from datetime import datetime, timezone
from app.extensions import db


class QueueEntry(db.Model):
    """
    One token/ticket a student holds. `position` is recalculated
    whenever entries ahead of it are completed or cancelled, rather
    than stored as a fixed number forever — see
    app/student/routes.py for how position is derived.
    """

    __tablename__ = "queue_entries"

    STATUS_WAITING = "waiting"
    STATUS_CALLED = "called"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"

    id = db.Column(db.Integer, primary_key=True)
    token_number = db.Column(db.String(20), unique=True, nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)

    status = db.Column(db.String(20), nullable=False, default=STATUS_WAITING)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    called_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    payment = db.relationship("Payment", backref="queue_entry", uselist=False)

    def __repr__(self):
        return f"<QueueEntry {self.token_number} ({self.status})>"