
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from flask import Blueprint, request, jsonify, current_app

from app.models.anomaly import Anomaly
from app.models.category import Category
from app.models.sector import Sector

from app.services.permissions import (
    current_user,
    role_required,
    ROLE_ADMIN,
    ROLE_CHEF,
)

from app.services.powerpoint_service import generate_powerpoint
from app.services.report_email_service import send_powerpoint_report


reports_bp = Blueprint(
    "reports",
    __name__,
    url_prefix="/api/reports"
)

LOCAL_TZ = ZoneInfo("Africa/Casablanca")


def _parse_ids(value, field_name):
    if value is None:
        return None

    if not isinstance(value, list):
        raise ValueError(
            f"{field_name} doit être une liste d'identifiants."
        )

    try:
        ids = list(dict.fromkeys(int(item) for item in value))
    except (TypeError, ValueError):
        raise ValueError(
            f"Identifiants invalides dans {field_name}."
        )

    if any(item <= 0 for item in ids):
        raise ValueError(
            f"Identifiants invalides dans {field_name}."
        )

    return ids


def _get_accessible_sector_ids(user):
    if user.role == ROLE_ADMIN:
        return [
            sector.id
            for sector in Sector.query.filter_by(
                is_active=True
            ).all()
        ]

    if user.role == ROLE_CHEF:
        return [
            sector.id
            for sector in user.sectors
            if sector.is_active
        ]

    return []


# ==================================================
# GET : OPTIONS DISPONIBLES POUR LE RAPPORT
# ADMIN ET CHEF_SECTEUR UNIQUEMENT
# ==================================================

@reports_bp.get("/options")
@role_required(ROLE_ADMIN, ROLE_CHEF)
def report_options():

    user = current_user()

    if not user:
        return jsonify({
            "status": "error",
            "message": "Utilisateur introuvable ou désactivé."
        }), 401

    accessible_sector_ids = _get_accessible_sector_ids(user)

    sectors = (
        Sector.query
        .filter(
            Sector.id.in_(accessible_sector_ids),
            Sector.is_active.is_(True)
        )
        .order_by(Sector.name.asc())
        .all()
    )

    categories = (
        Category.query
        .filter_by(is_active=True)
        .order_by(Category.name.asc())
        .all()
    )

    return jsonify({
        "status": "success",
        "sectors": [
            sector.to_dict()
            for sector in sectors
        ],
        "categories": [
            category.to_dict()
            for category in categories
        ]
    }), 200


# ==================================================
# POST : GENERATION ET ENVOI DU RAPPORT POWERPOINT
# ADMIN ET CHEF_SECTEUR UNIQUEMENT
# ==================================================

@reports_bp.post("/powerpoint")
@role_required(ROLE_ADMIN, ROLE_CHEF)
def export_powerpoint_report():

    user = current_user()

    if not user:
        return jsonify({
            "status": "error",
            "message": "Utilisateur introuvable ou désactivé."
        }), 401

    data = request.get_json(silent=True) or {}

    start_value = data.get("start_date")
    end_value = data.get("end_date")

    if not start_value or not end_value:
        return jsonify({
            "status": "error",
            "message": "Les dates de début et de fin sont obligatoires."
        }), 400

    try:
        start_date = datetime.strptime(
            start_value,
            "%Y-%m-%d"
        ).date()

        end_date = datetime.strptime(
            end_value,
            "%Y-%m-%d"
        ).date()

    except (TypeError, ValueError):
        return jsonify({
            "status": "error",
            "message": "Format de date invalide. Utilisez AAAA-MM-JJ."
        }), 400

    if end_date < start_date:
        return jsonify({
            "status": "error",
            "message": (
                "La date de fin doit être supérieure "
                "ou égale à la date de début."
            )
        }), 400

    try:
        requested_sector_ids = _parse_ids(
            data.get("sector_ids"),
            "sector_ids"
        )

        requested_category_ids = _parse_ids(
            data.get("category_ids"),
            "category_ids"
        )

    except ValueError as error:
        return jsonify({
            "status": "error",
            "message": str(error)
        }), 400

    # ----------------------------------------------
    # VERIFICATION DES SECTEURS AUTORISES
    # ----------------------------------------------

    accessible_sector_ids = _get_accessible_sector_ids(user)

    if requested_sector_ids is None:
        selected_sector_ids = accessible_sector_ids

    else:
        if not requested_sector_ids:
            return jsonify({
                "status": "error",
                "message": "Sélectionnez au moins un secteur."
            }), 400

        unauthorized_ids = (
            set(requested_sector_ids)
            - set(accessible_sector_ids)
        )

        if unauthorized_ids:
            return jsonify({
                "status": "error",
                "message": (
                    "Vous ne pouvez pas exporter "
                    "les secteurs non autorisés."
                )
            }), 403

        selected_sector_ids = requested_sector_ids

    if not selected_sector_ids:
        return jsonify({
            "status": "error",
            "message": "Aucun secteur accessible pour cet utilisateur."
        }), 403

    # ----------------------------------------------
    # VERIFICATION DES CATEGORIES
    # ----------------------------------------------

    if requested_category_ids is None:
        selected_category_ids = None

        selected_categories = (
            Category.query
            .filter_by(is_active=True)
            .order_by(Category.name.asc())
            .all()
        )

    else:
        if not requested_category_ids:
            return jsonify({
                "status": "error",
                "message": "Sélectionnez au moins une catégorie."
            }), 400

        selected_categories = (
            Category.query
            .filter(
                Category.id.in_(requested_category_ids),
                Category.is_active.is_(True)
            )
            .all()
        )

        existing_category_ids = {
            category.id
            for category in selected_categories
        }

        if existing_category_ids != set(requested_category_ids):
            return jsonify({
                "status": "error",
                "message": (
                    "Une ou plusieurs catégories sont introuvables "
                    "ou désactivées."
                )
            }), 400

        selected_category_ids = requested_category_ids

    # ----------------------------------------------
    # PERIODE INCLUSIVE - HEURE DU MAROC
    # ----------------------------------------------

    start_datetime = datetime.combine(
        start_date,
        time.min
    ).replace(tzinfo=LOCAL_TZ)

    end_datetime_exclusive = datetime.combine(
        end_date + timedelta(days=1),
        time.min
    ).replace(tzinfo=LOCAL_TZ)

    # ----------------------------------------------
    # RECHERCHE DES ANOMALIES
    # ----------------------------------------------

    query = Anomaly.query.filter(
        Anomaly.created_at >= start_datetime,
        Anomaly.created_at < end_datetime_exclusive,
        Anomaly.sector_id.in_(selected_sector_ids)
    )

    if selected_category_ids is not None:
        query = query.filter(
            Anomaly.category_id.in_(selected_category_ids)
        )

    anomalies = query.order_by(
        Anomaly.created_at.desc(),
        Anomaly.id.desc()
    ).all()

    # ----------------------------------------------
    # GENERATION DU POWERPOINT
    # ----------------------------------------------

    try:
        powerpoint_file = generate_powerpoint(
            anomalies=anomalies,
            start_date=start_date,
            end_date=end_date,
            upload_folder=current_app.config["UPLOAD_FOLDER"]
        )

        filename = (
            f"rapport_zero_anomalie_"
            f"{start_date.strftime('%Y%m%d')}_"
            f"{end_date.strftime('%Y%m%d')}.pptx"
        )

        selected_sectors = (
            Sector.query
            .filter(Sector.id.in_(selected_sector_ids))
            .order_by(Sector.name.asc())
            .all()
        )

        sector_names = [
            sector.name
            for sector in selected_sectors
        ]

        category_names = [
            category.name
            for category in selected_categories
        ]

        # ------------------------------------------
        # ENVOI AUTOMATIQUE PAR E-MAIL
        # ------------------------------------------

        email_sent, email_message = send_powerpoint_report(
            powerpoint_file=powerpoint_file,
            filename=filename,
            start_date=start_date,
            end_date=end_date,
            sector_names=sector_names,
            category_names=category_names
        )

        if not email_sent:
            return jsonify({
                "status": "error",
                "message": email_message,
                "report_generated": True,
                "email_sent": False
            }), 502

        current_app.logger.info(
            "Rapport généré et envoyé. "
            "Utilisateur=%s, anomalies=%s",
            user.username,
            len(anomalies)
        )

        return jsonify({
            "status": "success",
            "message": (
                "Le rapport PowerPoint a été généré "
                "et envoyé par e-mail avec succès."
            ),
            "recipient": "i.elayyate@iam.ma",
            "filename": filename,
            "anomalies_count": len(anomalies),
            "sectors": sector_names,
            "categories": category_names,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d")
        }), 200

    except Exception:
        current_app.logger.exception(
            "Erreur pendant la génération ou l'envoi "
            "du rapport PowerPoint."
        )

        return jsonify({
            "status": "error",
            "message": (
                "Une erreur est survenue pendant "
                "la génération ou l'envoi du rapport."
            )
        }), 500
