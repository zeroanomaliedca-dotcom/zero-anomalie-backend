
from functools import wraps

from flask import jsonify
from flask_jwt_extended import (
    get_jwt_identity,
    verify_jwt_in_request,
)

from app.models import User, Sector


ROLE_ADMIN = "ADMIN"
ROLE_CHEF = "CHEF_SECTEUR"
ROLE_TECHNICIEN = "TECHNICIEN"


def current_user():
    """Retourne l'utilisateur authentifié, actif et non supprimé."""

    user_id = get_jwt_identity()

    if not user_id:
        return None

    try:
        user = User.query.get(int(user_id))
    except (TypeError, ValueError):
        return None

    if (
        not user
        or not user.is_active
        or user.deleted_at is not None
    ):
        return None

    return user


def role_required(*allowed_roles):
    """Protège une route selon les rôles autorisés."""

    def decorator(view_function):
        @wraps(view_function)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()

            user = current_user()

            if not user:
                return jsonify({
                    "status": "error",
                    "message": "Utilisateur introuvable, désactivé ou supprimé."
                }), 401

            if user.role not in allowed_roles:
                return jsonify({
                    "status": "error",
                    "message": "Accès non autorisé."
                }), 403

            return view_function(*args, **kwargs)

        return wrapper

    return decorator


def user_can_access_sector(user, sector_id):
    """
    Vérifie si un utilisateur peut accéder à un secteur.

    ADMIN : tous les secteurs actifs.
    CHEF_SECTEUR : tous les secteurs actifs.
    TECHNICIEN : aucun accès supplémentaire par cette fonction.
    """

    if (
        not user
        or user.deleted_at is not None
        or not user.is_active
    ):
        return False

    if user.role in (ROLE_ADMIN, ROLE_CHEF):
        return Sector.query.filter_by(
            id=sector_id,
            is_active=True
        ).first() is not None

    return False


def user_can_access_anomaly(user, anomaly):
    """
    Vérifie les droits d'accès à une anomalie.

    ADMIN : toutes les anomalies.
    CHEF_SECTEUR : toutes les anomalies des trois secteurs.
    TECHNICIEN : uniquement ses propres anomalies.
    """

    if (
        not user
        or not anomaly
        or user.deleted_at is not None
        or not user.is_active
    ):
        return False

    if user.role in (ROLE_ADMIN, ROLE_CHEF):
        return True

    if user.role == ROLE_TECHNICIEN:
        return anomaly.technician_id == user.id

    return False


def get_accessible_sector_ids(user):
    """
    Retourne les secteurs accessibles selon le rôle.

    ADMIN : tous les secteurs actifs.
    CHEF_SECTEUR : tous les secteurs actifs.
    TECHNICIEN : aucun secteur supplémentaire.
    """

    if (
        not user
        or user.deleted_at is not None
        or not user.is_active
    ):
        return []

    if user.role in (ROLE_ADMIN, ROLE_CHEF):
        return [
            sector.id
            for sector in Sector.query.filter_by(
                is_active=True
            ).all()
        ]

    return []
