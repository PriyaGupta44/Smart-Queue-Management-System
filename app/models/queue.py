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
    STATUS_SKIPPED = "skipped"

    id = db.Column(db.Integer, primary_key=True)
    token_number = db.Column(db.String(20), unique=True, nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)

    status = db.Column(db.String(20), nullable=False, default=STATUS_WAITING, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    called_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    payment = db.relationship("Payment", backref="queue_entry", uselist=False)

    def __repr__(self):
        return f"<QueueEntry {self.token_number} ({self.status})>"

@classmethod
def average_service_minutes(cls):
        """Real average service time from the last 20 completed
        entries. Falls back to 5.0 minutes when there's no history."""
        recent_completed = (
            cls.query.filter(
                cls.status == cls.STATUS_COMPLETED,
                cls.called_at.isnot(None),
                cls.completed_at.isnot(None),
            )
            .order_by(cls.completed_at.desc())
            .limit(20)
            .all()
        )
        if not recent_completed:
            return 5.0
        total_seconds = sum((e.completed_at - e.called_at).total_seconds() for e in recent_completed)
        return max((total_seconds / len(recent_completed)) / 60, 1.0)