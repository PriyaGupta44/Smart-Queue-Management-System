from flask import Flask

from config import config
from app.extensions import db, login_manager, csrf, migrate, mail


def create_app(config_name="default"):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

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

    return app


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