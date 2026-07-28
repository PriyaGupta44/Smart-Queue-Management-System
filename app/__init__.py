import os
import logging
from logging.handlers import RotatingFileHandler

from flask import Flask, render_template
from flask_wtf.csrf import CSRFError

from config import config
from app.extensions import db, login_manager, csrf, migrate, mail


def create_app(config_name="default"):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)
    mail.init_app(app)

    from app.main.routes import main_bp
    from app.auth.routes import auth_bp
    from app.student.routes import student_bp
    from app.admin.routes import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(student_bp, url_prefix="/student")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    from app.models import student, queue, payment  # noqa: F401

    register_cli(app)
    configure_logging(app)
    register_error_handlers(app)

    return app


def configure_logging(app):
    """Write errors and warnings to a rotating log file on disk.

    Skipped entirely during tests (app.testing) — pytest already
    captures stdout/stderr per test, and creating real log files on
    every test run would just be noise and disk churn.
    """
    if app.testing:
        return

    project_root = os.path.dirname(app.root_path)
    log_dir = os.path.join(project_root, "logs")
    os.makedirs(log_dir, exist_ok=True)

    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "app.log"),
        maxBytes=1_000_000,  # rotate after ~1MB
        backupCount=5,       # keep 5 old log files before deleting the oldest
    )
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s: %(message)s [in %(pathname)s:%(lineno)d]"
        )
    )
    file_handler.setLevel(logging.INFO)

    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info("Application startup")


def register_error_handlers(app):
    """Custom pages for common HTTP errors, instead of Flask's bare
    defaults or (in debug mode) the interactive debugger."""

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        # Specific to CSRF failures — Flask matches this before the
        # more general 400 handler below, since CSRFError is a more
        # specific exception class than a plain BadRequest.
        app.logger.warning("CSRF validation failed: %s", error.description)
        return render_template(
            "errors/generic.html",
            error_code=400,
            error_title="Bad Request",
            error_message="Your form submission could not be verified. Please go back and try again.",
        ), 400

    @app.errorhandler(400)
    def bad_request(error):
        return render_template(
            "errors/generic.html",
            error_code=400,
            error_title="Bad Request",
            error_message="The request could not be understood. Please try again.",
        ), 400

    @app.errorhandler(403)
    def forbidden(error):
        return render_template(
            "errors/generic.html",
            error_code=403,
            error_title="Access Denied",
            error_message="You do not have permission to view this page.",
        ), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template(
            "errors/generic.html",
            error_code=404,
            error_title="Page Not Found",
            error_message="The page you are looking for does not exist or may have been moved.",
        ), 404

    @app.errorhandler(500)
    def internal_error(error):
        # A failed request may have left a half-finished database
        # transaction pending on this session. Roll it back so the
        # next request isn't affected by whatever went wrong here.
        db.session.rollback()
        app.logger.exception("Unhandled exception")
        return render_template(
            "errors/generic.html",
            error_code=500,
            error_title="Something Went Wrong",
            error_message="We have logged the issue and are looking into it. Please try again in a few moments.",
        ), 500


def register_cli(app):
    import click

    @app.cli.command("seed-admin")
    @click.argument("email")
    @click.argument("full_name")
    @click.password_option()
    def seed_admin(email, full_name, password):
        from app.extensions import db
        from app.models.student import Student

        email = email.lower()
        existing = Student.query.filter_by(email=email).first()
        if existing:
            existing.role = Student.ROLE_ADMIN
            existing.set_password(password)
            db.session.commit()
            click.echo(f"Existing user {email} promoted to admin.")
            return

        admin = Student(full_name=full_name, email=email, role=Student.ROLE_ADMIN)
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        click.echo(f"Admin account created for {email}.")


def configure_logging(app):
    if app.testing:
        return

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s [in %(pathname)s:%(lineno)d]"
    )

    # Always log to stdout — most hosting platforms (Heroku, Render,
    # Railway, etc.) capture and centrally aggregate stdout/stderr,
    # and their filesystems are often ephemeral, so a log FILE alone
    # would be silently lost on every restart or redeploy there.
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.INFO)
    app.logger.addHandler(stream_handler)

    # Also keep a local rotating file — useful for a traditional VPS
    # deployment with persistent disk; harmless (just redundant) on
    # platforms where it won't survive a restart.
    project_root = os.path.dirname(app.root_path)
    log_dir = os.path.join(project_root, "logs")
    os.makedirs(log_dir, exist_ok=True)

    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "app.log"), maxBytes=1_000_000, backupCount=5
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)

    app.logger.setLevel(logging.INFO)
    app.logger.info("Application startup")