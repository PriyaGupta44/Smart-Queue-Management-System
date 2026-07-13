from flask import Flask

from config import config
from app.extensions import db, login_manager, csrf


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

    return app