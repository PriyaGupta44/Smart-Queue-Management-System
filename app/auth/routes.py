from flask import Blueprint, render_template, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from flask_mail import Message

from app.extensions import db, mail
from app.models.student import Student
from app.auth.forms import RegisterForm, LoginForm, ForgotPasswordForm, ResetPasswordForm

auth_bp = Blueprint("auth", __name__, template_folder="../templates/auth")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("student.dashboard"))

    form = RegisterForm()
    if form.validate_on_submit():
        existing = Student.query.filter_by(email=form.email.data.lower()).first()
        if existing:
            flash("An account with that email already exists.", "danger")
            return render_template("register.html", form=form)

        student = Student(full_name=form.full_name.data, email=form.email.data.lower())
        student.set_password(form.password.data)
        db.session.add(student)
        db.session.commit()

        flash("Account created — you can log in now.", "success")
        return redirect(url_for("auth.login"))

    return render_template("register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("student.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        student = Student.query.filter_by(email=form.email.data.lower()).first()

        if student is None or not student.check_password(form.password.data):
            flash("Invalid email or password.", "danger")
            return render_template("login.html", form=form)

        login_user(student, remember=form.remember_me.data)

        if student.is_admin:
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("student.dashboard"))

    return render_template("login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("main.home"))


def _send_reset_email(student, reset_url):
    """Send the password reset email.

    Failures are logged, not raised. forgot_password() always shows the
    same generic message regardless of whether sending succeeded — if
    we let a send failure surface differently to the user, that would
    leak information about which emails are registered, defeating the
    whole point of the generic message.
    """
    message = Message(
        subject="Reset your Queue Management System password",
        recipients=[student.email],
        body=render_template("email/reset_password.txt", student=student, reset_url=reset_url),
        html=render_template("email/reset_password.html", student=student, reset_url=reset_url),
    )
    try:
        mail.send(message)
    except Exception:
        # Broad except is deliberate here: SMTP failures can surface as
        # several different exception types (connection errors, auth
        # errors, timeouts), and none of them should crash the request
        # or change what the user sees. We still want the full error
        # logged for ourselves, which is what .exception() does.
        current_app.logger.exception("Failed to send password reset email to %s", student.email)


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
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

    return render_template("forgot_password.html", form=form)


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

    return render_template("reset_password.html", form=form)