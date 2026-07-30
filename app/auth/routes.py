from flask import Blueprint, render_template, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from flask_mail import Message

from app.extensions import db, mail, limiter
from app.models.student import Student
from app.auth.forms import RegisterForm, LoginForm, ForgotPasswordForm, ResetPasswordForm

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
@limiter.limit("5 per hour")
def register():
    if current_user.is_authenticated:
        return redirect(url_for("student.dashboard"))

    form = RegisterForm()
    if form.validate_on_submit():
        existing = Student.query.filter_by(email=form.email.data.lower()).first()
        if existing:
            flash("An account with that email already exists.", "danger")
            return render_template("auth/register.html", form=form)

        student = Student(full_name=form.full_name.data, email=form.email.data.lower())
        student.set_password(form.password.data)
        db.session.add(student)
        db.session.commit()

        flash("Account created — you can log in now.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("student.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        student = Student.query.filter_by(email=form.email.data.lower()).first()

        if student is not None and student.is_locked():
            flash(
                "This account is temporarily locked due to repeated failed login attempts. "
                "Please try again later.",
                "danger",
            )
            return render_template("auth/login.html", form=form)

        if student is None or not student.check_password(form.password.data):
            if student is not None:
                student.register_failed_login()
                db.session.commit()
            flash("Invalid email or password.", "danger")
            return render_template("auth/login.html", form=form)

        student.register_successful_login()
        db.session.commit()

        login_user(student, remember=form.remember_me.data)

        if student.is_admin:
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("student.dashboard"))

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.home"))


def _send_reset_email(student, reset_url):
    message = Message(
        subject="Reset your Queue Management System password",
        recipients=[student.email],
        body=render_template("email/reset_password.txt", student=student, reset_url=reset_url),
        html=render_template("email/reset_password.html", student=student, reset_url=reset_url),
    )
    try:
        mail.send(message)
    except Exception:
        current_app.logger.exception("Failed to send password reset email to %s", student.email)


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("3 per hour")
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("student.dashboard"))

    form = ForgotPasswordForm()
    if form.validate_on_submit():
        student = Student.query.filter_by(email=form.email.data.lower()).first()

        if student:
            token = student.get_reset_token()
            reset_url = url_for("auth.reset_password", token=token, _external=True)
            _send_reset_email(student, reset_url)

        flash("If an account with that email exists, a reset link has been sent.", "info")
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html", form=form)


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("student.dashboard"))

    student = Student.verify_reset_token(token)
    if student is None:
        flash("That reset link is invalid or has expired.", "danger")
        return redirect(url_for("auth.forgot_password"))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        student.set_password(form.password.data)
        db.session.commit()
        flash("Your password has been reset. You can log in now.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", form=form)