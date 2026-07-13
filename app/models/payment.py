from datetime import datetime, timezone
from app.extensions import db


class Payment(db.Model):
    """A simulated fee payment tied to one queue entry/token."""

    __tablename__ = "payments"

    STATUS_PENDING = "pending"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"

    id = db.Column(db.Integer, primary_key=True)
    queue_entry_id = db.Column(db.Integer, db.ForeignKey("queue_entries.id"), nullable=False)

    amount = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.String(20), nullable=False, default=STATUS_PENDING)
    receipt_number = db.Column(db.String(30), unique=True, nullable=True)
    paid_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Payment {self.receipt_number} ({self.status})>"