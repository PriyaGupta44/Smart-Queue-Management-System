"""Tests for environment-specific config validation."""

import pytest
from flask import Flask

from config import ProductionConfig


def test_production_config_requires_secret_key():
    app = Flask(__name__)
    app.config.from_object(ProductionConfig)
    app.config["SECRET_KEY"] = None  # simulate a deployment that forgot to set it

    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        ProductionConfig.init_app(app)


def test_production_config_passes_with_secret_key_set():
    app = Flask(__name__)
    app.config.from_object(ProductionConfig)
    app.config["SECRET_KEY"] = "a-real-secret-key"

    ProductionConfig.init_app(app)  # should not raise