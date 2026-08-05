import csv
import io
from flask import Response

from functools import wraps
from datetime import datetime, timedelta, timezone

from flask import Blueprint, render_template, redirect, url_for, flash, abort, request, current_app
from flask_login import login_required, current_user
from sqlalchemy import or_
from flask_mail import Message

from app.extensions import db, mail
from app.models.queue import QueueEntry
from app.models.payment import Payment
from app.models.student import Student

from app.admin.forms import AddStudentForm

admin_bp = Blueprint("admin", __name__)

DASHBOARD_PER_PAGE = 10


def admin_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not current_user.is_admin:
            abort(403)
        return view_func(*args, **kwargs)

    return wrapped

def _send_token_called_email(entry):
    message = Message(
        subject=f"Your token {entry.token_number} has been called",
        recipients=[entry.student.email],
        body=render_template("email/token_called.txt", entry=entry),
    )
    try:
        mail.send(message)
    except Exception:
        current_app.logger.exception("Failed to send token-called email to %s", entry.student.email)


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
    _send_token_called_email(entry)
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
    _send_token_called_email(entry)
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


@admin_bp.route("/export/students.csv")
@login_required
@admin_required
def export_students_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Email", "Registered On"])
    for student in Student.query.filter_by(role=Student.ROLE_STUDENT).order_by(Student.created_at).all():
        writer.writerow([
            student.full_name,
            student.email,
            student.created_at.strftime("%Y-%m-%d") if student.created_at else "",
        ])
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=students.csv"},
    )


@admin_bp.route("/export/payments.csv")
@login_required
@admin_required
def export_payments_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Receipt", "Token", "Student", "Amount", "Status", "Paid At"])
    for payment in Payment.query.order_by(Payment.created_at.desc()).all():
        writer.writerow([
            payment.receipt_number or "",
            payment.queue_entry.token_number,
            payment.queue_entry.student.full_name,
            payment.amount,
            payment.status,
            payment.paid_at.strftime("%Y-%m-%d %H:%M") if payment.paid_at else "",
        ])
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=payments.csv"},
    )


@admin_bp.route("/students/add", methods=["GET", "POST"])
@login_required
@admin_required
def add_student():
    form = AddStudentForm()
    if form.validate_on_submit():
        existing = Student.query.filter_by(email=form.email.data.lower()).first()
        if existing:
            flash("An account with that email already exists.", "danger")
            return render_template("admin/add_student.html", form=form)

        student = Student(full_name=form.full_name.data, email=form.email.data.lower())
        student.set_password(form.password.data)
        db.session.add(student)
        db.session.commit()

        flash(f"Student {student.full_name} added.", "success")
        return redirect(url_for("admin.students"))

    return render_template("admin/add_student.html", form=form)