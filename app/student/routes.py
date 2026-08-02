import os
from werkzeug.utils import secure_filename

from datetime import datetime, timezone
import random

from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from flask import Blueprint, render_template, redirect, url_for, flash, jsonify, current_app
from flask_mail import Message

from app.student.forms import ProfileForm, ChangePasswordForm
from app.extensions import db, mail
from app.models.queue import QueueEntry
from app.models.payment import Payment

student_bp = Blueprint("student", __name__)

MAX_TOKEN_GENERATION_ATTEMPTS = 5

def _send_password_changed_email(student):
    message = Message(
        subject="Your password was changed",
        recipients=[student.email],
        body=render_template("email/password_changed.txt", student=student),
    )
    try:
        mail.send(message)
    except Exception:
        current_app.logger.exception("Failed to send password-changed email to %s", student.email)

def _generate_token_number():
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"Q-{today}-{random.randint(1000, 9999)}"


def _position_in_queue(entry):
    if entry.status != QueueEntry.STATUS_WAITING:
        return None
    ahead = QueueEntry.query.filter(
        QueueEntry.status == QueueEntry.STATUS_WAITING,
        QueueEntry.created_at < entry.created_at,
    ).count()
    return ahead + 1


def _average_minutes_per_token():
    return QueueEntry.average_service_minutes()

@student_bp.route("/dashboard")
@login_required
def dashboard():
    active_entry = (
        current_user.queue_entries.filter(
            QueueEntry.status.in_([QueueEntry.STATUS_WAITING, QueueEntry.STATUS_CALLED])
        ).first()
    )
    position = _position_in_queue(active_entry) if active_entry else None
    return render_template("student/dashboard.html", entry=active_entry, position=position)


@student_bp.route("/queue/join", methods=["POST"])
@login_required
def join_queue():
    already_active = current_user.queue_entries.filter(
        QueueEntry.status.in_([QueueEntry.STATUS_WAITING, QueueEntry.STATUS_CALLED])
    ).first()
    if already_active:
        flash("You already have an active token.", "warning")
        return redirect(url_for("student.dashboard"))

    for attempt in range(MAX_TOKEN_GENERATION_ATTEMPTS):
        entry = QueueEntry(token_number=_generate_token_number(), student_id=current_user.id)
        db.session.add(entry)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            continue
        else:
            flash(f"Joined the queue — your token is {entry.token_number}.", "success")
            return redirect(url_for("student.dashboard"))

    flash("We could not generate a queue token right now. please try again in a moment.", "danger")
    return redirect(url_for("student.dashboard"))


@student_bp.route("/queue/status")
@login_required
def queue_status():
    entry = (
        current_user.queue_entries.filter(
            QueueEntry.status.in_([QueueEntry.STATUS_WAITING, QueueEntry.STATUS_CALLED])
        ).first()
    )
    if not entry:
        flash("You don't have an active queue token.", "info")
        return redirect(url_for("student.dashboard"))

    position = _position_in_queue(entry)
    eta_minutes = round(position * _average_minutes_per_token()) if position else None
    return render_template(
        "student/queue_status.html", entry=entry, position=position, eta_minutes=eta_minutes
    )

@student_bp.route("/queue/status/data")
@login_required
def queue_status_data():
    """JSON version of queue_status(), polled by the page's JS every
    10 seconds instead of reloading the whole page."""
    entry = (
        current_user.queue_entries.filter(
            QueueEntry.status.in_([QueueEntry.STATUS_WAITING, QueueEntry.STATUS_CALLED])
        ).first()
    )
    if not entry:
        return jsonify({"active": False})

    position = _position_in_queue(entry)
    eta_minutes = round(position * _average_minutes_per_token()) if position else None

    return jsonify(
        {
            "active": True,
            "status": entry.status,
            "token_number": entry.token_number,
            "position": position,
            "eta_minutes": eta_minutes,
        }
    )

@student_bp.route("/payment/<int:entry_id>/pay", methods=["POST"])
@login_required
def pay(entry_id):
    entry = current_user.queue_entries.filter_by(id=entry_id).first_or_404()

    if entry.payment and entry.payment.status == Payment.STATUS_SUCCESS:
        flash("This token has already been paid for.", "info")
        return redirect(url_for("student.dashboard"))

    payment = entry.payment or Payment(queue_entry_id=entry.id, amount=500.00)
    payment.status = Payment.STATUS_SUCCESS
    payment.paid_at = datetime.now(timezone.utc)
    payment.receipt_number = f"RCPT-{entry.token_number}"

    db.session.add(payment)
    db.session.commit()

    flash(
        f"🎉 Congratulations! Your payment was successful. Receipt: {payment.receipt_number}",
        "success",
    )
    return redirect(url_for("student.dashboard"))


@student_bp.route("/payments")
@login_required
def payment_history():
    payments = (
        Payment.query.join(QueueEntry)
        .filter(QueueEntry.student_id == current_user.id)
        .order_by(Payment.created_at.desc())
        .all()
    )
    return render_template("student/payment_history.html", payments=payments)


@student_bp.route("/payments/<int:payment_id>/receipt")
@login_required
def receipt(payment_id):
    # Filtering on QueueEntry.student_id == current_user.id here (not
    # just Payment.id) is what prevents one student from viewing
    # another student's receipt by guessing/incrementing the URL — an
    # IDOR vulnerability if this only checked that the payment exists.
    payment = (
        Payment.query.join(QueueEntry)
        .filter(Payment.id == payment_id, QueueEntry.student_id == current_user.id)
        .first_or_404()
    )
    return render_template("student/receipt.html", payment=payment)


@student_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    if form.validate_on_submit():
        current_user.full_name = form.full_name.data

        if form.avatar.data:
            filename = f"{current_user.id}_{secure_filename(form.avatar.data.filename)}"
            upload_dir = os.path.join(current_app.root_path, "static", "uploads", "avatars")
            os.makedirs(upload_dir, exist_ok=True)
            form.avatar.data.save(os.path.join(upload_dir, filename))
            current_user.avatar_filename = filename

        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for("student.profile"))
    return render_template("student/profile.html", form=form)

@student_bp.route("/profile/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash("Current password is incorrect.", "danger")
            return render_template("student/change_password.html", form=form)

        current_user.set_password(form.new_password.data)
        db.session.commit()
        _send_password_changed_email(current_user)
        flash("Password changed successfully.", "success")
        return redirect(url_for("student.profile"))

    return render_template("student/change_password.html", form=form)


@student_bp.route("/queue/cancel", methods=["POST"])
@login_required
def cancel_queue():
    # Only a WAITING entry can be self-cancelled — once called, the
    # student needs to actually show up or let it lapse; cancelling
    # mid-service would leave the admin flow in a confusing state.
    entry = current_user.queue_entries.filter_by(status=QueueEntry.STATUS_WAITING).first()
    if not entry:
        flash("You don't have a waiting token to cancel.", "warning")
        return redirect(url_for("student.dashboard"))

    entry.status = QueueEntry.STATUS_CANCELLED
    db.session.commit()
    flash(f"Token {entry.token_number} has been cancelled.", "info")
    return redirect(url_for("student.dashboard"))