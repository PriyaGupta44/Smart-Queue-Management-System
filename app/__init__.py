from flask import Flask

from config import config
from app.extensions import db, login_manager, csrf, migrate


def create_app(config_name="default"):
    """
    Application factory. Building the app inside a function (instead of
    at module level like the old app.py) means:
      - tests can spin up a fresh app with TestingConfig
      - extensions get attached to the app cleanly (no circular imports)
      - nothing runs a dev server just from being imported
    """
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # --- attach extensions to this app instance ---
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    # render_as_batch=True: SQLite can't ALTER a table to add a CHECK
    # constraint in place like Postgres/MySQL can. Batch mode has
    # Alembic instead recreate the table with the new constraint and
    # copy the data over. Only matters for SQLite; harmless elsewhere.
    migrate.init_app(app, db, render_as_batch=True)

    # --- register blueprints ---
    from app.main.routes import main_bp
    from app.auth.routes import auth_bp
    from app.student.routes import student_bp
    from app.admin.routes import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(student_bp, url_prefix="/student")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    # --- models must be imported so Flask-Migrate/db.create_all can see them ---
    from app.models import student, queue, payment  # noqa: F401

    register_cli(app)

    return app


def register_cli(app):
    """CLI commands, kept separate from HTTP routes on purpose.

    Admin accounts must never be created through the public /register
    form (that would let anyone grant themselves admin access). This
    command is the only supported way to create one:

        flask --app run.py seed-admin admin@college.edu "Admin Name"
    """
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