
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from app.extensions import db
from app.models import User, Sector
from app.services.permissions import role_required, current_user


users_bp = Blueprint(
    "users",
    __name__,
    url_prefix="/api/users"
)


# =====================================================
# 1. CONSULTER LES UTILISATEURS NON SUPPRIMES
# =====================================================

@users_bp.get("")
@jwt_required()
@role_required("ADMIN")
def list_users():

    users = User.query.filter(
        User.deleted_at.is_(None)
    ).order_by(User.created_at.desc()).all()

    return jsonify({
        "status": "success",
        "total": len(users),
        "users": [user.to_dict() for user in users]
    }), 200


# =====================================================
# 2. CREER UN UTILISATEUR
# =====================================================

@users_bp.post("")
@jwt_required()
@role_required("ADMIN")
def create_user():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "message": "Données JSON invalides."
        }), 400

    username = data.get("username")
    full_name = data.get("full_name")
    password = data.get("password")
    role = data.get("role")
    sector_ids = data.get("sector_ids", [])

    if not all([username, full_name, password, role]):
        return jsonify({
            "status": "error",
            "message": "Tous les champs obligatoires doivent être renseignés."
        }), 400

    if not isinstance(username, str) or not isinstance(full_name, str):
        return jsonify({
            "status": "error",
            "message": "Nom d'utilisateur ou nom complet invalide."
        }), 400

    if not isinstance(role, str):
        return jsonify({
            "status": "error",
            "message": "Rôle invalide."
        }), 400

    username = username.strip()
    full_name = full_name.strip()
    role = role.strip().upper()

    if not username or not full_name:
        return jsonify({
            "status": "error",
            "message": "Le nom d'utilisateur et le nom complet sont obligatoires."
        }), 400

    if len(username) > 80 or len(full_name) > 150:
        return jsonify({
            "status": "error",
            "message": "Longueur maximale dépassée."
        }), 400

    if not isinstance(password, str) or len(password) < 12:
        return jsonify({
            "status": "error",
            "message": "Le mot de passe doit contenir au moins 12 caractères."
        }), 400

    if role not in ["TECHNICIEN", "CHEF_SECTEUR"]:
        return jsonify({
            "status": "error",
            "message": "Rôle invalide. ADMIN ne peut pas être créé par cette route."
        }), 400

    if User.query.filter_by(username=username).first():
        return jsonify({
            "status": "error",
            "message": "Ce nom d'utilisateur existe déjà."
        }), 409

    if not isinstance(sector_ids, list):
        return jsonify({
            "status": "error",
            "message": "sector_ids doit être une liste."
        }), 400

    if role == "CHEF_SECTEUR" and not sector_ids:
        return jsonify({
            "status": "error",
            "message": "Un chef doit être affecté à au moins un secteur."
        }), 400

    if role == "TECHNICIEN" and sector_ids:
        return jsonify({
            "status": "error",
            "message": "Un technicien ne peut pas recevoir d'affectation fixe de secteur."
        }), 400

    if any(type(sid) is not int or sid <= 0 for sid in sector_ids):
        return jsonify({
            "status": "error",
            "message": "Identifiant de secteur invalide."
        }), 400

    if len(sector_ids) != len(set(sector_ids)):
        return jsonify({
            "status": "error",
            "message": "La liste contient des secteurs en double."
        }), 400

    sectors = []

    if sector_ids:
        sectors = Sector.query.filter(
            Sector.id.in_(sector_ids),
            Sector.is_active.is_(True)
        ).all()

        if len(sectors) != len(sector_ids):
            return jsonify({
                "status": "error",
                "message": "Un ou plusieurs secteurs sont inexistants ou inactifs."
            }), 400

    user = User(
        username=username,
        full_name=full_name,
        role=role,
        is_active=True,
        sectors=sectors
    )

    user.set_password(password)

    try:
        db.session.add(user)
        db.session.commit()

    except Exception:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": "Impossible de créer le compte."
        }), 500

    return jsonify({
        "status": "success",
        "message": "Compte créé avec succès.",
        "user": user.to_dict()
    }), 201


# =====================================================
# 3. MODIFIER UN UTILISATEUR
# =====================================================

@users_bp.put("/<int:user_id>")
@jwt_required()
@role_required("ADMIN")
def update_user(user_id):

    user = db.session.get(User, user_id)

    if not user or user.deleted_at is not None:
        return jsonify({
            "status": "error",
            "message": "Utilisateur introuvable."
        }), 404

    if user.role == "ADMIN":
        return jsonify({
            "status": "error",
            "message": "La modification d'un compte ADMIN est interdite."
        }), 403

    data = request.get_json(silent=True)

    if not isinstance(data, dict) or not data:
        return jsonify({
            "status": "error",
            "message": "Données JSON invalides ou vides."
        }), 400

    allowed_fields = {
        "full_name",
        "role",
        "password",
        "sector_ids"
    }

    if not set(data.keys()).issubset(allowed_fields):
        return jsonify({
            "status": "error",
            "message": "Un ou plusieurs champs ne sont pas autorisés."
        }), 400

    new_full_name = user.full_name
    new_role = user.role
    new_password = data.get("password")
    new_sector_ids = data.get("sector_ids")

    if "full_name" in data:

        if not isinstance(data["full_name"], str):
            return jsonify({
                "status": "error",
                "message": "Nom complet invalide."
            }), 400

        new_full_name = data["full_name"].strip()

        if not new_full_name or len(new_full_name) > 150:
            return jsonify({
                "status": "error",
                "message": "Le nom complet est obligatoire et limité à 150 caractères."
            }), 400

    if "role" in data:

        if not isinstance(data["role"], str):
            return jsonify({
                "status": "error",
                "message": "Rôle invalide."
            }), 400

        new_role = data["role"].strip().upper()

        if new_role not in ["TECHNICIEN", "CHEF_SECTEUR"]:
            return jsonify({
                "status": "error",
                "message": "Seuls les rôles TECHNICIEN et CHEF_SECTEUR sont autorisés."
            }), 400

    if new_password is not None:

        if not isinstance(new_password, str) or len(new_password) < 12:
            return jsonify({
                "status": "error",
                "message": "Le nouveau mot de passe doit contenir au moins 12 caractères."
            }), 400

    if new_sector_ids is not None:

        if not isinstance(new_sector_ids, list):
            return jsonify({
                "status": "error",
                "message": "sector_ids doit être une liste."
            }), 400

        if any(
            type(sid) is not int or sid <= 0
            for sid in new_sector_ids
        ):
            return jsonify({
                "status": "error",
                "message": "Identifiant de secteur invalide."
            }), 400

        if len(new_sector_ids) != len(set(new_sector_ids)):
            return jsonify({
                "status": "error",
                "message": "La liste contient des secteurs en double."
            }), 400

    if new_role == "TECHNICIEN":

        if new_sector_ids:
            return jsonify({
                "status": "error",
                "message": "Un technicien ne peut pas avoir de secteur affecté."
            }), 400

        sectors = []

    else:

        if new_sector_ids is None:

            if user.role == "CHEF_SECTEUR":
                sectors = list(user.sectors)

            else:
                return jsonify({
                    "status": "error",
                    "message": "Un chef doit être affecté à au moins un secteur."
                }), 400

        else:

            if not new_sector_ids:
                return jsonify({
                    "status": "error",
                    "message": "Un chef doit être affecté à au moins un secteur."
                }), 400

            sectors = Sector.query.filter(
                Sector.id.in_(new_sector_ids),
                Sector.is_active.is_(True)
            ).all()

            if len(sectors) != len(new_sector_ids):
                return jsonify({
                    "status": "error",
                    "message": "Un ou plusieurs secteurs sont inexistants ou inactifs."
                }), 400

    user.full_name = new_full_name
    user.role = new_role
    user.sectors = sectors

    if new_password is not None:
        user.set_password(new_password)

    try:
        db.session.commit()

    except Exception:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": "Impossible de modifier le compte."
        }), 500

    return jsonify({
        "status": "success",
        "message": "Compte modifié avec succès.",
        "user": user.to_dict()
    }), 200


# =====================================================
# 4. ACTIVER / DESACTIVER UN UTILISATEUR
# =====================================================

@users_bp.patch("/<int:user_id>/status")
@jwt_required()
@role_required("ADMIN")
def update_user_status(user_id):

    admin = current_user()

    if not admin:
        return jsonify({
            "status": "error",
            "message": "Administrateur non autorisé."
        }), 401

    if admin.id == user_id:
        return jsonify({
            "status": "error",
            "message": "Vous ne pouvez pas désactiver votre propre compte."
        }), 403

    user = db.session.get(User, user_id)

    if not user or user.deleted_at is not None:
        return jsonify({
            "status": "error",
            "message": "Utilisateur introuvable."
        }), 404

    if user.role == "ADMIN":
        return jsonify({
            "status": "error",
            "message": "Impossible de modifier le statut d'un compte ADMIN."
        }), 403

    data = request.get_json(silent=True)

    if not isinstance(data, dict) or type(data.get("is_active")) is not bool:
        return jsonify({
            "status": "error",
            "message": "Le champ is_active doit être true ou false."
        }), 400

    user.is_active = data["is_active"]

    try:
        db.session.commit()

    except Exception:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": "Impossible de modifier le statut du compte."
        }), 500

    return jsonify({
        "status": "success",
        "message": "Statut du compte modifié avec succès.",
        "user": user.to_dict()
    }), 200


# =====================================================
# 5. SUPPRESSION LOGIQUE D'UN UTILISATEUR
# =====================================================

@users_bp.delete("/<int:user_id>")
@jwt_required()
@role_required("ADMIN")
def delete_user(user_id):

    admin = current_user()

    if not admin:
        return jsonify({
            "status": "error",
            "message": "Administrateur non autorisé."
        }), 401

    if admin.id == user_id:
        return jsonify({
            "status": "error",
            "message": "Vous ne pouvez pas supprimer votre propre compte."
        }), 403

    user = db.session.get(User, user_id)

    if not user or user.deleted_at is not None:
        return jsonify({
            "status": "error",
            "message": "Utilisateur introuvable."
        }), 404

    if user.role == "ADMIN":
        return jsonify({
            "status": "error",
            "message": "La suppression d'un compte ADMIN est interdite."
        }), 403

    user.deleted_at = datetime.now(timezone.utc)
    user.is_active = False

    try:
        db.session.commit()

    except Exception:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": "Impossible de supprimer le compte."
        }), 500

    return jsonify({
        "status": "success",
        "message": "Compte supprimé. Son historique est conservé."
    }), 200
