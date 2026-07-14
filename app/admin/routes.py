from functools import wraps
from datetime import datetime, timezone

from flask import Blueprint, render_template, redirect, url_for, flash, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models.queue import QueueEntry
from app.models.payment import Payment

admin_bp = Blueprint("admin", __name__, template_folder="../templates/admin")


def admin_required(view_func):
    """Same idea as @login_required, but also checks role == 'admin'.
    Stacks on top of @login_required (below it), so an anonymous user
    gets redirected to login first, and a logged-in non-admin gets a
    403 rather than silently seeing the login page again."""

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view_func(*args, **kwargs)

    return wrapped


@admin_bp.route("/dashboard")
@login_required
@admin_required
def dashboard():
    waiting = QueueEntry.query.filter_by(status=QueueEntry.STATUS_WAITING).order_by(
        QueueEntry.created_at.asc()
    ).all()
    called = QueueEntry.query.filter_by(status=QueueEntry.STATUS_CALLED).all()
    return render_template("dashboard.html", waiting=waiting, called=called)


@admin_bp.route("/queue/<int:entry_id>/call", methods=["POST"])
@login_required
@admin_required
def call_next(entry_id):
    entry = QueueEntry.query.get_or_404(entry_id)
    entry.status = QueueEntry.STATUS_CALLED
    entry.called_at = datetime.now(timezone.utc)
    db.session.commit()
    flash(f"Called {entry.token_number}.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/queue/<int:entry_id>/complete", methods=["POST"])
@login_required
@admin_required
def complete(entry_id):
    entry = QueueEntry.query.get_or_404(entry_id)
    entry.status = QueueEntry.STATUS_COMPLETED
    entry.completed_at = datetime.now(timezone.utc)
    db.session.commit()
    flash(f"Marked {entry.token_number} as completed.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/payments")
@login_required
@admin_required
def payments():
    records = Payment.query.order_by(Payment.created_at.desc()).all()
    return render_template("payments.html", payments=records)