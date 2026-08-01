from functools import wraps
from datetime import datetime, timedelta, timezone

from flask import Blueprint, render_template, redirect, url_for, flash, abort, request
from flask_login import login_required, current_user
from sqlalchemy import or_

from app.extensions import db
from app.models.queue import QueueEntry
from app.models.payment import Payment
from app.models.student import Student

admin_bp = Blueprint("admin", __name__)

DASHBOARD_PER_PAGE = 10


def admin_required(view_func):
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

    # New for Day 30 (Commit 3): fetch skipped entries so the dashboard
    # can show a "Skipped — Needs Recall" section. Deliberately NOT
    # paginated — see the note in the original instructions about why.
    skipped_entries = (
        QueueEntry.query.join(Student)
        .filter(QueueEntry.status == QueueEntry.STATUS_SKIPPED)
        .order_by(QueueEntry.created_at.asc())
        .all()
    )

    return render_template(
        "admin/dashboard.html",
        waiting=waiting_pagination.items,
        called=called_pagination.items,
        waiting_pagination=waiting_pagination,
        called_pagination=called_pagination,
        search=search,
        skipped=skipped_entries,
    )

@admin_bp.route("/queue/<int:entry_id>/call", methods=["POST"])
@login_required
@admin_required
def call_next(entry_id):
    entry = db.session.get(QueueEntry, entry_id)
    if entry is None:
        abort(404)

    if entry.status != QueueEntry.STATUS_WAITING:
        flash(f"{entry.token_number} is not waiting and cannot be called.", "warning")
        return redirect(url_for("admin.dashboard"))

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

    if entry.status != QueueEntry.STATUS_CALLED:
        flash(f"{entry.token_number} must be called before it can be completed.", "warning")
        return redirect(url_for("admin.dashboard"))

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
    return render_template("admin/payments.html", payments=records)


STUDENTS_PER_PAGE = 15


@admin_bp.route("/students")
@login_required
@admin_required
def students():
    search = request.args.get("q", "").strip()
    page = request.args.get("page", 1, type=int)

    query = Student.query.filter(Student.role == Student.ROLE_STUDENT)

    if search:
        like_pattern = f"%{search}%"
        query = query.filter(
            or_(Student.full_name.ilike(like_pattern), Student.email.ilike(like_pattern))
        )

    query = query.order_by(Student.created_at.desc())
    pagination = query.paginate(page=page, per_page=STUDENTS_PER_PAGE, error_out=False)

    return render_template(
        "admin/students.html",
        students=pagination.items,
        pagination=pagination,
        search=search,
    )


@admin_bp.route("/students/<int:student_id>")
@login_required
@admin_required
def student_detail(student_id):
    student = Student.query.filter_by(id=student_id, role=Student.ROLE_STUDENT).first_or_404()
    entries = (
        QueueEntry.query.filter_by(student_id=student.id)
        .order_by(QueueEntry.created_at.desc())
        .all()
    )
    return render_template("admin/student_detail.html", student=student, entries=entries)



@admin_bp.route("/queue/<int:entry_id>/skip", methods=["POST"])
@login_required
@admin_required
def skip(entry_id):
    entry = QueueEntry.query.get_or_404(entry_id)

    if entry.status != QueueEntry.STATUS_CALLED:
        flash(f"{entry.token_number} must be called before it can be skipped.", "warning")
        return redirect(url_for("admin.dashboard"))

    entry.status = QueueEntry.STATUS_SKIPPED
    db.session.commit()
    flash(f"{entry.token_number} marked as skipped (no-show).", "warning")
    return redirect(url_for("admin.dashboard"))

@admin_bp.route("/queue/<int:entry_id>/recall", methods=["POST"])
@login_required
@admin_required
def recall(entry_id):
    entry = QueueEntry.query.get_or_404(entry_id)

    if entry.status != QueueEntry.STATUS_SKIPPED:
        flash(f"{entry.token_number} is not skipped and cannot be recalled.", "warning")
        return redirect(url_for("admin.dashboard"))

    entry.status = QueueEntry.STATUS_CALLED
    entry.called_at = datetime.now(timezone.utc)
    db.session.commit()
    flash(f"{entry.token_number} recalled.", "success")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/stats")
@login_required
@admin_required
def stats():
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    total_students = Student.query.filter_by(role=Student.ROLE_STUDENT).count()
    active_queue = QueueEntry.query.filter(
        QueueEntry.status.in_([QueueEntry.STATUS_WAITING, QueueEntry.STATUS_CALLED])
    ).count()
    completed_today = QueueEntry.query.filter(
        QueueEntry.status == QueueEntry.STATUS_COMPLETED,
        QueueEntry.completed_at >= today_start,
    ).count()
    avg_wait_minutes = round(QueueEntry.average_service_minutes(), 1)

    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent_entries = QueueEntry.query.filter(QueueEntry.created_at >= week_ago).all()
    hourly_counts = [0] * 24
    for entry in recent_entries:
        if entry.created_at:
            hourly_counts[entry.created_at.hour] += 1

    return render_template(
        "admin/stats.html",
        total_students=total_students,
        active_queue=active_queue,
        completed_today=completed_today,
        avg_wait_minutes=avg_wait_minutes,
        hourly_counts=hourly_counts,
    )