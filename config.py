import os
from datetime import timedelta
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))


class Config:
    """Base configuration — shared by every environment."""

    # No insecure fallback here at the base level — each environment
    # below decides explicitly what happens if SECRET_KEY is missing.
    SECRET_KEY = os.environ.get("SECRET_KEY")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(basedir, "instance", "app.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Email (used for password reset links) ---
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", MAIL_USERNAME)

    # --- Rate limiting ---
    # "memory://" (the default) keeps counts in this process's RAM —
    # fine for a single-process deployment, but each gunicorn worker
    # would have its OWN separate counts if run with multiple workers.
    # A shared backend (e.g. Redis, "redis://localhost:6379") would be
    # needed for correct limits across multiple worker processes.
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_ENABLED = True

    # --- Cookie security ---
    SESSION_COOKIE_NAME = "qms_session"  # avoid the default "session" name, which fingerprints Flask
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Secure means "only send this cookie over HTTPS." Left False by
    # default here because local development runs over plain HTTP —
    # a Secure cookie simply never gets sent/stored in that case,
    # which would silently break login locally. ProductionConfig
    # below forces this True unconditionally.
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"

    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    REMEMBER_COOKIE_DURATION = timedelta(days=14)  # Flask-Login's own default is 365 days — too long

    @staticmethod
    def init_app(app):
        """Hook for environment-specific startup checks. Base class
        does nothing; subclasses override to validate their own
        requirements (see ProductionConfig below)."""
        pass

    PERMANENT_SESSION_LIFETIME = timedelta(
        minutes=int(os.environ.get("SESSION_IDLE_TIMEOUT_MINUTES", 30))
    )


class DevelopmentConfig(Config):
    DEBUG = True
    # A fallback is acceptable ONLY here — local development, never
    # deployed, never handling a real user's data.
    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-only-insecure-key-do-not-use-in-production"


class TestingConfig(Config):
    TESTING = True
    SECRET_KEY = "testing-only-key"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False  # simplifies posting forms in tests
    MAIL_SUPPRESS_SEND = True  # never actually contact an SMTP server in tests
    # Flask-Mail asserts a message has *some* sender before it even
    # checks MAIL_SUPPRESS_SEND, so a dummy value is required here even
    # though no real email is ever sent during tests.
    MAIL_DEFAULT_SENDER = "noreply@example.com"
    RATELIMIT_ENABLED = False  # never let rate limits interfere with the rest of the suite


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True

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