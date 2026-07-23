from datetime import datetime, timezone
import random

from flask import Blueprint, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models.queue import QueueEntry
from app.models.payment import Payment

student_bp = Blueprint("student", __name__, template_folder="../templates/student")

# How many times to retry generating a token number if two requests
# collide on the same random value. 5 is generous — even at the old,
# narrower random range, the odds of colliding 5 times in a row are
# vanishingly small; this is a safety net, not the expected path.
MAX_TOKEN_GENERATION_ATTEMPTS = 5


def _generate_token_number():
    """Daily token like 'Q-20260713-4231'.

    Uniqueness isn't actually guaranteed by this function alone — two
    concurrent requests can still compute the same number. What makes
    tokens genuinely unique is the UNIQUE constraint on
    QueueEntry.token_number at the database level, combined with the
    retry loop in join_queue() below. Widening the range here (from
    3 digits to 4) just makes that retry path rarer in practice.
    """
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"Q-{today}-{random.randint(1000, 9999)}"


def _position_in_queue(entry):
    """A student's position = how many WAITING entries were created
    before theirs. Computed on read instead of stored, so it's always
    correct even after other entries are completed or cancelled."""
    if entry.status != QueueEntry.STATUS_WAITING:
        return None
    ahead = QueueEntry.query.filter(
        QueueEntry.status == QueueEntry.STATUS_WAITING,
        QueueEntry.created_at < entry.created_at,
    ).count()
    return ahead + 1


@student_bp.route("/dashboard")
@login_required
def dashboard():
    active_entry = (
        current_user.queue_entries.filter(
            QueueEntry.status.in_([QueueEntry.STATUS_WAITING, QueueEntry.STATUS_CALLED])
        ).first()
    )
    position = _position_in_queue(active_entry) if active_entry else None
    return render_template("dashboard.html", entry=active_entry, position=position)


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
            # Another request landed on the same token number at the
            # same moment. The database's UNIQUE constraint is what
            # actually caught it — roll back the failed insert and
            # try again with a fresh number, instead of trusting our
            # own randomness to never collide.
            db.session.rollback()
            continue
        else:
            flash(f"Joined the queue — your token is {entry.token_number}.", "success")
            return redirect(url_for("student.dashboard"))

    # Every attempt collided — extraordinarily unlikely, but fail
    # honestly instead of crashing with a raw 500 page.
    flash("We couldn't generate a queue token right now — please try again in a moment.", "danger")
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
    return render_template("queue_status.html", entry=entry, position=position)


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

    flash("Payment successful.", "success")
    return redirect(url_for("student.dashboard"))