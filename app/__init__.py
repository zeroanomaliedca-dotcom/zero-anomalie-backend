
import os

from flask import Flask, jsonify

from config import Config
from app.extensions import db, migrate, jwt, cors


def create_app():
    app = Flask(__name__)

    app.config.from_object(Config)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    cors.init_app(
        app,
        resources={r"/api/*": {"origins": "*"}}
    )

    from app import models

    from app.routes.auth import auth_bp
    from app.routes.anomalies import anomalies_bp
    from app.routes.anomaly_photos import anomaly_photos_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.users import users_bp
    from app.routes.categories import categories_bp
    from app.routes.sectors import sectors_bp
    from app.routes.reports import reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(anomalies_bp)
    app.register_blueprint(anomaly_photos_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(categories_bp)
    app.register_blueprint(sectors_bp)
    app.register_blueprint(reports_bp)

    @app.get("/api/health")
    def health():
        return jsonify({
            "status": "success",
            "message": "API ZERO ANOMALIE operationnelle."
        }), 200

    @app.get("/")
    def index():
        return jsonify({
            "status": "success",
            "message": "Bienvenue sur l'API ZERO ANOMALIE."
        }), 200

    return app
