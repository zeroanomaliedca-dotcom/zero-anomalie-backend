
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from app.services.permissions import current_user
from app.services.dashboard_service import (
    get_dashboard_statistics,
    get_technician_challenge,
)


dashboard_bp = Blueprint(
    "dashboard",
    __name__,
    url_prefix="/api/dashboard"
)


@dashboard_bp.get("")
@jwt_required()
def get_dashboard():
    user = current_user()

    if not user or not user.is_active or user.deleted_at is not None:
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


@dashboard_bp.get("/challenge")
@jwt_required()
def get_challenge():
    user = current_user()

    if not user or not user.is_active or user.deleted_at is not None:
        return jsonify({
            "status": "error",
            "message": "Utilisateur non autorisé."
        }), 401

    if user.role not in (
        "ADMIN",
        "CHEF_SERVICE",
        "CHEF_SECTEUR",
        "TECHNICIEN",
    ):
        return jsonify({
            "status": "error",
            "message": "Accès refusé."
        }), 403

    ranking = get_technician_challenge()

    return jsonify({
        "status": "success",
        "challenge": ranking,
        "total_technicians": len(ranking),
    }), 200
