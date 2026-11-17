
from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    get_jwt_identity,
    get_jwt,
    jwt_required,
)

from app.models import User


auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}

    username = str(data.get("username", "")).strip()
    password = data.get("password", "")

    if not username or not isinstance(password, str) or not password:
        return jsonify({
            "status": "error",
            "message": "Identifiant et mot de passe obligatoires."
        }), 400

    user = User.query.filter_by(username=username).first()

    if not user or not user.check_password(password):
        return jsonify({
            "status": "error",
            "message": "Identifiant ou mot de passe incorrect."
        }), 401

    if user.deleted_at is not None:
        return jsonify({
            "status": "error",
            "message": "Ce compte a été supprimé."
        }), 403

    if not user.is_active:
        return jsonify({
            "status": "error",
            "message": "Ce compte est désactivé."
        }), 403

    sector_ids = [sector.id for sector in user.sectors]

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={
            "role": user.role,
            "sector_ids": sector_ids,
        }
    )

    return jsonify({
        "status": "success",
        "message": "Connexion réussie.",
        "access_token": access_token,
        "token_type": "Bearer",
        "user": user.to_dict(),
    }), 200


@auth_bp.get("/me")
@jwt_required()
def me():
    user_id = get_jwt_identity()

    try:
        user = User.query.get(int(user_id))
    except (TypeError, ValueError):
        user = None

    if not user or not user.is_active or user.deleted_at is not None:
        return jsonify({
            "status": "error",
            "message": "Utilisateur introuvable, désactivé ou supprimé."
        }), 401

    return jsonify({
        "status": "success",
        "user": user.to_dict(),
        "permissions": {
            "role": get_jwt().get("role"),
            "sector_ids": get_jwt().get("sector_ids", []),
        }
    }), 200
