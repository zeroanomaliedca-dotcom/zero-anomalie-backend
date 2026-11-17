
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
    user_can_access_sector,
)

from app.services.anomaly_service import (
    create_anomaly,
    AnomalyValidationError,
)

from app.services.anomaly_query_service import get_anomalies_for_user
from app.services.treatment_service import update_anomaly_status
from app.services.email_service import send_declaration_notification

anomalies_bp = Blueprint(
    "anomalies",
    __name__,
    url_prefix="/api/anomalies"
)

@anomalies_bp.post("")
@jwt_required()
@role_required("ADMIN", "CHEF_SECTEUR", "TECHNICIEN")
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

        # Le chef de secteur ne peut déclarer que dans son propre secteur.
        if (
            user.role == "CHEF_SECTEUR"
            and not user_can_access_sector(user, sector_id)
        ):
            return jsonify({
                "status": "error",
                "message": "Vous ne pouvez déclarer une anomalie que dans votre secteur."
            }), 403

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

@anomalies_bp.get("")
@jwt_required()
def list_anomalies():
    user = current_user()

    if not user:
        return jsonify({
            "status": "error",
            "message": "Utilisateur introuvable ou désactivé."
        }), 401

    anomalies = get_anomalies_for_user(user)

    return jsonify({
        "status": "success",
        "count": len(anomalies),
        "anomalies": [
            anomaly.to_dict()
            for anomaly in anomalies
        ]
    }), 200

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

@anomalies_bp.patch("/<int:anomaly_id>/status")
@jwt_required()
@role_required("ADMIN", "CHEF_SECTEUR")
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