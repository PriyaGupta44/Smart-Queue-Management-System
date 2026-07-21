"""
Central place to create Flask extension instances.

These are created WITHOUT an app attached. Each one is bound to the
real app later, inside create_app(), via extension.init_app(app).

Why this file exists: models.py needs `db`, routes.py needs `db` and
`login_manager`, and app/__init__.py needs all of them. If we created
these directly inside app/__init__.py, importing models would require
importing the app package, and importing the app package would require
the models to already exist -> circular import. Keeping them here
breaks that cycle.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from flask_migrate import Migrate


db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()
migrate = Migrate()

# Where Flask-Login sends anonymous users who hit a @login_required route
login_manager.login_view = "auth.login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "info"