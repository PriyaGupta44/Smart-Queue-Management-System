from functools import wraps
from datetime import datetime, timezone

from flask import Blueprint, render_template, redirect, url_for, flash, abort, request
from flask_login import login_required, current_user
from sqlalchemy import or_

from app.extensions import db
from app.models.queue import QueueEntry
from app.models.payment import Payment
from app.models.student import Student

admin_bp = Blueprint("admin", __name__, template_folder="../templates/admin")

# Rows per page on the admin dashboard tables. A module-level constant
# rather than a magic number in the route — easy to find, easy to tune.
DASHBOARD_PER_PAGE = 10


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
    search = request.args.get("q", "").strip()
    waiting_page = request.args.get("waiting_page", 1, type=int)
    called_page = request.args.get("called_page", 1, type=int)

    waiting_query = (
        QueueEntry.query.join(Student)
        .filter(QueueEntry.status == QueueEntry.STATUS_WAITING)
    )
    called_query = (
        QueueEntry.query.join(Student)
        .filter(QueueEntry.status == QueueEntry.STATUS_CALLED)
    )

    if search:
        like_pattern = f"%{search}%"
        search_filter = or_(
            Student.full_name.ilike(like_pattern),
            Student.email.ilike(like_pattern),
            QueueEntry.token_number.ilike(like_pattern),
        )
        waiting_query = waiting_query.filter(search_filter)
        called_query = called_query.filter(search_filter)

    waiting_query = waiting_query.order_by(QueueEntry.created_at.asc())
    called_query = called_query.order_by(QueueEntry.called_at.desc())

    waiting_pagination = waiting_query.paginate(
        page=waiting_page, per_page=DASHBOARD_PER_PAGE, error_out=False
    )
    called_pagination = called_query.paginate(
        page=called_page, per_page=DASHBOARD_PER_PAGE, error_out=False
    )

    return render_template(
        "dashboard.html",
        waiting=waiting_pagination.items,
        called=called_pagination.items,
        waiting_pagination=waiting_pagination,
        called_pagination=called_pagination,
        search=search,
    )


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