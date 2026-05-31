from flask import Flask
from flask_cors import CORS

from app.config import Config
from app.extensions import db, migrate


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app, origins=app.config["CORS_ORIGINS"])

    from app import models  # noqa: F401
    from app.routes import api_bp

    app.register_blueprint(api_bp)

    return app
