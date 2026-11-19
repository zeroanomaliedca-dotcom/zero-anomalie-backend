
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func

from app.extensions import db
from app.models.sector import Sector
from app.services.permissions import current_user, role_required


sectors_bp = Blueprint(
    "sectors",
    __name__,
    url_prefix="/api/sectors"
)


# ==========================================
# GET : LISTE DES SECTEURS
# ADMIN : tous les secteurs
# CHEF_SECTEUR : uniquement ses secteurs actifs
# TECHNICIEN : tous les secteurs actifs
# ==========================================
@sectors_bp.get("")
@jwt_required()
def list_sectors():
    user = current_user()

    if not user:
        return jsonify({
            "status": "error",
            "message": "Utilisateur non autorisé."
        }), 401

    query = Sector.query

    if user.role == "ADMIN":
        # L'administrateur voit tous les secteurs,
        # y compris les secteurs désactivés.
        pass

    elif user.role == "CHEF_SECTEUR":
        # Le chef de secteur voit uniquement
        # les secteurs qui lui sont attribués et actifs.
        assigned_sector_ids = [
            sector.id
            for sector in user.sectors
            if sector.is_active
        ]

        query = query.filter(
            Sector.id.in_(assigned_sector_ids)
        )

    else:
        # Les autres utilisateurs voient tous les secteurs actifs.
        query = query.filter_by(is_active=True)

    sectors = query.order_by(Sector.name.asc()).all()

    return jsonify({
        "status": "success",
        "count": len(sectors),
        "sectors": [sector.to_dict() for sector in sectors]
    }), 200


# ==========================================
# POST : CREATION D'UN SECTEUR
# ADMIN uniquement
# ==========================================
@sectors_bp.post("")
@jwt_required()
@role_required("ADMIN")
def create_sector():
    data = request.get_json(silent=True) or {}

    name = data.get("name")

    if not isinstance(name, str) or not name.strip():
        return jsonify({
            "status": "error",
            "message": "Le nom du secteur est obligatoire."
        }), 400

    name = name.strip()

    if len(name) > 100:
        return jsonify({
            "status": "error",
            "message": "Le nom ne doit pas dépasser 100 caractères."
        }), 400

    existing = Sector.query.filter(
        func.lower(Sector.name) == name.lower()
    ).first()

    if existing:
        return jsonify({
            "status": "error",
            "message": "Ce secteur existe déjà."
        }), 409

    sector = Sector(
        name=name,
        is_active=True
    )

    try:
        db.session.add(sector)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Secteur créé avec succès.",
            "sector": sector.to_dict()
        }), 201

    except Exception:
        db.session.rollback()

        return jsonify({
            "status": "error",
            "message": "Erreur lors de la création du secteur."
        }), 500


# ==========================================
# PUT : MODIFICATION D'UN SECTEUR
# ADMIN uniquement
# ==========================================
@sectors_bp.put("/<int:sector_id>")
@jwt_required()
@role_required("ADMIN")
def update_sector(sector_id):
    sector = db.session.get(Sector, sector_id)

    if not sector:
        return jsonify({
            "status": "error",
            "message": "Secteur introuvable."
        }), 404

    data = request.get_json(silent=True) or {}

    if "name" not in data:
        return jsonify({
            "status": "error",
            "message": "Aucune modification fournie."
        }), 400

    name = data["name"]

    if not isinstance(name, str) or not name.strip():
        return jsonify({
            "status": "error",
            "message": "Le nom du secteur est invalide."
        }), 400

    name = name.strip()

    if len(name) > 100:
        return jsonify({
            "status": "error",
            "message": "Le nom ne doit pas dépasser 100 caractères."
        }), 400

    existing = Sector.query.filter(
        func.lower(Sector.name) == name.lower(),
        Sector.id != sector_id
    ).first()

    if existing:
        return jsonify({
            "status": "error",
            "message": "Un autre secteur porte déjà ce nom."
        }), 409

    sector.name = name

    try:
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Secteur modifié avec succès.",
            "sector": sector.to_dict()
        }), 200

    except Exception:
        db.session.rollback()

        return jsonify({
            "status": "error",
            "message": "Erreur lors de la modification du secteur."
        }), 500


# ==========================================
# PATCH : ACTIVATION / DESACTIVATION
# ADMIN uniquement
# ==========================================
@sectors_bp.patch("/<int:sector_id>/status")
@jwt_required()
@role_required("ADMIN")
def update_sector_status(sector_id):
    sector = db.session.get(Sector, sector_id)

    if not sector:
        return jsonify({
            "status": "error",
            "message": "Secteur introuvable."
        }), 404

    data = request.get_json(silent=True) or {}
    is_active = data.get("is_active")

    if not isinstance(is_active, bool):
        return jsonify({
            "status": "error",
            "message": "Le champ is_active doit être true ou false."
        }), 400

    sector.is_active = is_active

    try:
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Statut du secteur modifié avec succès.",
            "sector": sector.to_dict()
        }), 200

    except Exception:
        db.session.rollback()

        return jsonify({
            "status": "error",
            "message": "Erreur lors du changement de statut."
        }), 500
