
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import func

from app.extensions import db
from app.models.category import Category
from app.services.permissions import current_user, role_required


categories_bp = Blueprint(
    "categories",
    __name__,
    url_prefix="/api/categories"
)


# ==========================================
# GET : LISTE DES CATEGORIES
# Accessible à tous les utilisateurs connectés
# ==========================================
@categories_bp.get("")
@jwt_required()
def list_categories():
    user = current_user()

    if not user:
        return jsonify({
            "status": "error",
            "message": "Utilisateur non autorisé."
        }), 401

    categories = Category.query.order_by(Category.name.asc()).all()

    return jsonify({
        "status": "success",
        "count": len(categories),
        "categories": [category.to_dict() for category in categories]
    }), 200


# ==========================================
# POST : CREATION D'UNE CATEGORIE
# ADMIN et CHEF_SERVICE
# ==========================================
@categories_bp.post("")
@jwt_required()
@role_required("ADMIN", "CHEF_SERVICE")
def create_category():
    data = request.get_json(silent=True) or {}

    name = data.get("name")

    if not isinstance(name, str) or not name.strip():
        return jsonify({
            "status": "error",
            "message": "Le nom de la catégorie est obligatoire."
        }), 400

    name = name.strip()
    description = data.get("description")

    if description is not None and not isinstance(description, str):
        return jsonify({
            "status": "error",
            "message": "La description doit être un texte."
        }), 400

    if len(name) > 150:
        return jsonify({
            "status": "error",
            "message": "Le nom ne doit pas dépasser 150 caractères."
        }), 400

    existing = Category.query.filter(
        func.lower(Category.name) == name.lower()
    ).first()

    if existing:
        return jsonify({
            "status": "error",
            "message": "Cette catégorie existe déjà."
        }), 409

    category = Category(
        name=name,
        description=description.strip() if description else None,
        is_active=True
    )

    try:
        db.session.add(category)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Catégorie créée avec succès.",
            "category": category.to_dict()
        }), 201

    except Exception:
        db.session.rollback()

        return jsonify({
            "status": "error",
            "message": "Erreur lors de la création de la catégorie."
        }), 500


# ==========================================
# PUT : MODIFICATION D'UNE CATEGORIE
# ADMIN et CHEF_SERVICE
# ==========================================
@categories_bp.put("/<int:category_id>")
@jwt_required()
@role_required("ADMIN", "CHEF_SERVICE")
def update_category(category_id):
    category = db.session.get(Category, category_id)

    if not category:
        return jsonify({
            "status": "error",
            "message": "Catégorie introuvable."
        }), 404

    data = request.get_json(silent=True) or {}

    if "name" in data:
        name = data["name"]

        if not isinstance(name, str) or not name.strip():
            return jsonify({
                "status": "error",
                "message": "Le nom de la catégorie est invalide."
            }), 400

        name = name.strip()

        if len(name) > 150:
            return jsonify({
                "status": "error",
                "message": "Le nom ne doit pas dépasser 150 caractères."
            }), 400

        existing = Category.query.filter(
            func.lower(Category.name) == name.lower(),
            Category.id != category_id
        ).first()

        if existing:
            return jsonify({
                "status": "error",
                "message": "Une autre catégorie porte déjà ce nom."
            }), 409

        category.name = name

    if "description" in data:
        description = data["description"]

        if description is not None and not isinstance(description, str):
            return jsonify({
                "status": "error",
                "message": "La description doit être un texte."
            }), 400

        category.description = description.strip() if description else None

    try:
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Catégorie modifiée avec succès.",
            "category": category.to_dict()
        }), 200

    except Exception:
        db.session.rollback()

        return jsonify({
            "status": "error",
            "message": "Erreur lors de la modification de la catégorie."
        }), 500


# ==========================================
# PATCH : ACTIVATION / DESACTIVATION
# ADMIN et CHEF_SERVICE
# ==========================================
@categories_bp.patch("/<int:category_id>/status")
@jwt_required()
@role_required("ADMIN", "CHEF_SERVICE")
def update_category_status(category_id):
    category = db.session.get(Category, category_id)

    if not category:
        return jsonify({
            "status": "error",
            "message": "Catégorie introuvable."
        }), 404

    data = request.get_json(silent=True) or {}
    is_active = data.get("is_active")

    if not isinstance(is_active, bool):
        return jsonify({
            "status": "error",
            "message": "Le champ is_active doit être true ou false."
        }), 400

    category.is_active = is_active

    try:
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Statut de la catégorie modifié avec succès.",
            "category": category.to_dict()
        }), 200

    except Exception:
        db.session.rollback()

        return jsonify({
            "status": "error",
            "message": "Erreur lors du changement de statut."
        }), 500
