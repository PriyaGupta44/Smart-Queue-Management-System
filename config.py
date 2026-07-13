import os
from dotenv import load_dotenv

# Load variables from a .env file in the project root (if present) into
# os.environ. Locally you'll have a real .env; in production you'd set
# these as real environment variables instead.
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, ".env"))


class Config:
    """Base config — shared by every environment."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-change-me")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///" + os.path.join(basedir, "instance", "app.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False  # simplifies posting forms in tests


class ProductionConfig(Config):
    DEBUG = False


config = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}