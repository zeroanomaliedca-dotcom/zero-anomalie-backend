
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from app.services.permissions import current_user
from app.services.dashboard_service import get_dashboard_statistics


dashboard_bp = Blueprint(
    "dashboard",
    __name__,
    url_prefix="/api/dashboard"
)


@dashboard_bp.get("")
@jwt_required()
def get_dashboard():
    user = current_user()

    if not user:
        return jsonify({
            "status": "error",
            "message": "Utilisateur non autorisé."
        }), 401

    statistics = get_dashboard_statistics(user)

    if statistics is None:
        return jsonify({
            "status": "error",
            "message": "Accès refusé."
        }), 403

    return jsonify({
        "status": "success",
        "dashboard": statistics
    }), 200
