
from pathlib import Path, PureWindowsPath

from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import SQLAlchemyError

from app.services.anomaly_detail_service import get_anomaly_details
from app.extensions import db
from app.models import Anomaly

from app.services.permissions import (
    current_user,
    role_required,
    user_can_access_anomaly,
)

from app.services.anomaly_service import (
    create_anomaly,
    AnomalyValidationError,
)

from app.services.anomaly_query_service import get_anomalies_for_user
from app.services.treatment_service import update_anomaly_status
from app.services.email_service import send_declaration_notification
from app.services.manual_email_service import send_manual_anomaly_email


anomalies_bp = Blueprint(
    "anomalies",
    __name__,
    url_prefix="/api/anomalies"
)


def get_safe_photo_path(file_path):
    """Retourne un chemin photo uniquement s'il reste dans UPLOAD_FOLDER."""

    if not isinstance(file_path, str) or not file_path.strip():
        return None

    normalized_path = file_path.replace("\\", "/")
    windows_path = PureWindowsPath(normalized_path)

    if (
        windows_path.is_absolute()
        or windows_path.drive
        or ".." in normalized_path.split("/")
        or normalized_path.startswith("/")
    ):
        return None

    upload_folder = Path(
        current_app.config["UPLOAD_FOLDER"]
    ).resolve()

    photo_path = (upload_folder / normalized_path).resolve()

    if not photo_path.is_relative_to(upload_folder):
        return None

    return photo_path


# ==========================================
# POST : CREATION D'UNE ANOMALIE
# ==========================================
@anomalies_bp.post("")
@jwt_required()
@role_required("ADMIN", "CHEF_SERVICE", "CHEF_SECTEUR", "TECHNICIEN")
def create_declaration():
    user = current_user()

    if not user:
        return jsonify({
            "status": "error",
            "message": "Utilisateur introuvable ou désactivé."
        }), 401

    data = request.form

    try:
        sector_id = int(data.get("sector_id", ""))
        category_id = int(data.get("category_id", ""))

        # Tous les rôles autorisés peuvent déclarer dans tout secteur actif.
        # Les droits de consultation restent gérés séparément.

        anomaly = create_anomaly(
            technician_id=user.id,
            sector_id=sector_id,
            category_id=category_id,
            title=data.get("title", ""),
            description=data.get("description", ""),
            declaration_method=data.get("declaration_method", ""),
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            location_address=data.get("location_address"),
            photos=request.files.getlist("photos"),
        )

        # Un échec d'e-mail ne doit jamais annuler la déclaration.
        email_sent, email_message = send_declaration_notification(anomaly)

        current_app.logger.info(
            "Notification déclaration %s : %s - %s",
            getattr(anomaly, "reference", anomaly.id),
            email_sent,
            email_message,
        )

        return jsonify({
            "status": "success",
            "message": "Anomalie déclarée avec succès.",
            "anomaly": anomaly.to_dict(),
            "email_notification": {
                "sent": email_sent,
                "message": email_message,
            },
        }), 201

    except (ValueError, TypeError):
        return jsonify({
            "status": "error",
            "message": "Identifiant de secteur ou de catégorie invalide."
        }), 400

    except AnomalyValidationError as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 400

    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception(
            "Erreur SQL lors de la déclaration d'une anomalie."
        )
        return jsonify({
            "status": "error",
            "message": "Erreur lors de l'enregistrement en base de données."
        }), 500

    except OSError:
        current_app.logger.exception(
            "Erreur lors de l'enregistrement des photos."
        )
        return jsonify({
            "status": "error",
            "message": "Erreur lors de l'enregistrement des photos."
        }), 500


# ==========================================
# GET : LISTE DES ANOMALIES
# ==========================================
@anomalies_bp.get("")
@jwt_required()
def list_anomalies():
    user = current_user()

    if not user:
        return jsonify({
            "status": "error",
            "message": "Utilisateur introuvable ou désactivé."
        }), 401

    reference = request.args.get("reference", "").strip()

    anomalies = get_anomalies_for_user(
        user,
        reference=reference
    )

    return jsonify({
        "status": "success",
        "count": len(anomalies),
        "anomalies": [
            anomaly.to_dict()
            for anomaly in anomalies
        ]
    }), 200


# ==========================================
# GET : MES ANOMALIES
# TECHNICIEN uniquement
# ==========================================
@anomalies_bp.get("/mine")
@jwt_required()
def my_anomalies():
    user = current_user()

    if not user:
        return jsonify({
            "status": "error",
            "message": "Utilisateur introuvable ou désactivé."
        }), 401

    if user.role != "TECHNICIEN":
        return jsonify({
            "status": "error",
            "message": "Cette route est réservée aux techniciens."
        }), 403

    anomalies = get_anomalies_for_user(user)

    return jsonify({
        "status": "success",
        "count": len(anomalies),
        "anomalies": [
            anomaly.to_dict()
            for anomaly in anomalies
        ]
    }), 200


# ==========================================
# PATCH : MODIFICATION DU STATUT
# ==========================================
@anomalies_bp.patch("/<int:anomaly_id>/status")
@jwt_required()
@role_required("ADMIN", "CHEF_SERVICE", "CHEF_SECTEUR")
def change_anomaly_status(anomaly_id):
    user = current_user()

    if not user:
        return jsonify({
            "status": "error",
            "message": "Utilisateur introuvable ou désactivé."
        }), 401

    anomaly = db.session.get(Anomaly, anomaly_id)

    if not anomaly:
        return jsonify({
            "status": "error",
            "message": "Anomalie introuvable."
        }), 404

    if not user_can_access_anomaly(user, anomaly):
        return jsonify({
            "status": "error",
            "message": "Vous n'avez pas accès à cette anomalie."
        }), 403

    new_status = request.form.get("new_status", "").strip()
    comment = request.form.get("comment", "").strip()
    photos = request.files.getlist("photos")

    if new_status not in (
        "EN_COURS_DE_TRAITEMENT",
        "TRAITEE"
    ):
        return jsonify({
            "status": "error",
            "message": "Le nouveau statut demandé est invalide."
        }), 400

    try:
        updated_anomaly = update_anomaly_status(
            anomaly=anomaly,
            user=user,
            new_status=new_status,
            comment=comment,
            photos=photos,
        )

        return jsonify({
            "status": "success",
            "message": "Statut de l'anomalie mis à jour avec succès.",
            "anomaly": updated_anomaly.to_dict(),
        }), 200

    except (ValueError, AnomalyValidationError) as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 400

    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception(
            "Erreur SQL lors de la mise à jour du statut."
        )
        return jsonify({
            "status": "error",
            "message": "Erreur lors de la mise à jour en base de données."
        }), 500

    except OSError:
        current_app.logger.exception(
            "Erreur lors de l'enregistrement des photos."
        )
        return jsonify({
            "status": "error",
            "message": "Erreur lors de l'enregistrement des photos."
        }), 500


# ==========================================
# POST : ENVOI MANUEL D'UN E-MAIL
# ADMIN et CHEF_SECTEUR uniquement
# ==========================================
@anomalies_bp.post("/<int:anomaly_id>/email")
@jwt_required()
@role_required("ADMIN", "CHEF_SECTEUR")
def send_anomaly_email(anomaly_id):
    user = current_user()

    if not user:
        return jsonify({
            "status": "error",
            "message": "Utilisateur introuvable ou désactivé."
        }), 401

    anomaly = db.session.get(Anomaly, anomaly_id)

    if not anomaly:
        return jsonify({
            "status": "error",
            "message": "Anomalie introuvable."
        }), 404

    if not user_can_access_anomaly(user, anomaly):
        return jsonify({
            "status": "error",
            "message": "Vous n'avez pas accès à cette anomalie."
        }), 403

    if anomaly.status != "EN_COURS_DE_TRAITEMENT":
        return jsonify({
            "status": "error",
            "message": "L'envoi manuel est disponible uniquement pour une anomalie en cours de traitement."
        }), 400

    data = request.get_json(silent=True) or {}
    recipients = data.get("recipients")

    sent, message = send_manual_anomaly_email(
        anomaly=anomaly,
        recipients=recipients,
    )

    if not sent:
        return jsonify({
            "status": "error",
            "message": message,
        }), 400

    return jsonify({
        "status": "success",
        "message": message,
        "reference": anomaly.reference,
    }), 200


# ==========================================
# GET : DETAIL D'UNE ANOMALIE
# ==========================================
@anomalies_bp.get("/<int:anomaly_id>")
@jwt_required()
def get_anomaly_detail(anomaly_id):
    user = current_user()

    if not user:
        return jsonify({
            "status": "error",
            "message": "Utilisateur introuvable ou désactivé."
        }), 401

    anomaly = db.session.get(Anomaly, anomaly_id)

    if not anomaly:
        return jsonify({
            "status": "error",
            "message": "Anomalie introuvable."
        }), 404

    if not user_can_access_anomaly(user, anomaly):
        return jsonify({
            "status": "error",
            "message": "Vous n'avez pas accès à cette anomalie."
        }), 403

    details = get_anomaly_details(anomaly)

    return jsonify({
        "status": "success",
        "anomaly": details,
    }), 200


# ==========================================
# DELETE : SUPPRESSION D'UNE ANOMALIE
# ADMIN uniquement
# ==========================================
@anomalies_bp.delete("/<int:anomaly_id>")
@jwt_required()
@role_required("ADMIN")
def delete_anomaly(anomaly_id):
    user = current_user()

    if not user:
        return jsonify({
            "status": "error",
            "message": "Utilisateur introuvable ou désactivé."
        }), 401

    anomaly = db.session.get(Anomaly, anomaly_id)

    if not anomaly:
        return jsonify({
            "status": "error",
            "message": "Anomalie introuvable."
        }), 404

    reference = anomaly.reference

    # Récupérer les chemins avant la suppression en base.
    photo_paths = [
        get_safe_photo_path(photo.file_path)
        for photo in anomaly.photos
    ]

    try:
        # Les relations cascade suppriment les photos et l'historique en BDD.
        db.session.delete(anomaly)
        db.session.commit()

    except SQLAlchemyError:
        db.session.rollback()
        current_app.logger.exception(
            "Erreur SQL lors de la suppression de l'anomalie %s.",
            reference
        )
        return jsonify({
            "status": "error",
            "message": "Impossible de supprimer l'anomalie en base de données."
        }), 500

    # Suppression physique après confirmation du commit.
    file_errors = 0

    for photo_path in photo_paths:
        if photo_path is None:
            file_errors += 1
            current_app.logger.warning(
                "Chemin photo invalide lors de la suppression de %s.",
                reference
            )
            continue

        try:
            photo_path.unlink(missing_ok=True)
        except OSError:
            file_errors += 1
            current_app.logger.exception(
                "Impossible de supprimer la photo %s.",
                photo_path
            )

    current_app.logger.info(
        "Anomalie %s supprimée par ADMIN %s.",
        reference,
        user.id
    )

    return jsonify({
        "status": "success",
        "message": "Anomalie supprimée avec succès.",
        "reference": reference,
        "photo_cleanup_warnings": file_errors,
    }), 200
