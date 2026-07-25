import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))


class Config:
    """Base config — shared by every environment."""

    # No insecure fallback here at the base level — each environment
    # below decides explicitly what happens if SECRET_KEY is missing.
    SECRET_KEY = os.environ.get("SECRET_KEY")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(basedir, "instance", "app.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", MAIL_USERNAME)

    @staticmethod
    def init_app(app):
        """Hook for environment-specific startup checks. Base class
        does nothing; subclasses override to validate their own
        requirements (see ProductionConfig below)."""
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    # A fallback is acceptable ONLY here — local development, never
    # deployed, never handling a real user's data.
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-only-insecure-key-do-not-use-in-production"


class TestingConfig(Config):
    TESTING = True
    SECRET_KEY = "testing-only-key"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    MAIL_SUPPRESS_SEND = True
    MAIL_DEFAULT_SENDER = "noreply@example.com"


class ProductionConfig(Config):
    DEBUG = False

    @staticmethod
    def init_app(app):
        if not app.config.get("SECRET_KEY"):
            raise RuntimeError(
                "SECRET_KEY environment variable must be set in production. "
                'Generate one with: python -c "import secrets; print(secrets.token_hex(32))"'
            )


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}