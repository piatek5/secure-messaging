import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from flask import Flask

from secure_messaging import models  # noqa: F401 (registers models with SQLAlchemy)
from secure_messaging.extensions import db


def create_app(test_config: Mapping[str, Any] | None = None) -> Flask:
    app = Flask(__name__, instance_path=os.environ.get("SECURE_MESSAGING_INSTANCE_PATH"))

    # Defaults
    database_path = Path(app.instance_path, "secure_messaging.sqlite")
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI=f"sqlite:///{database_path}",
    )

    if test_config is None:
        # Load the instance config from env when not testing
        app.config.from_prefixed_env()
    else:
        # Load the test config if passed in
        app.config.from_mapping(test_config)

    # Fail fast instead of running with an insecure default key
    if not app.config.get("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY is not set, set FLASK_SECRET_KEY in the environment")

    # Ensure the instance folder exists
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    db.init_app(app)

    @app.route("/api/health")
    def health():
        return {"status": "ok"}

    return app
