
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from flask import current_app

from app.extensions import db
from app.models import Anomaly, AnomalyPhoto, History
from app.services.permissions import user_can_access_anomaly
from app.services.anomaly_service import validate_photo, AnomalyValidationError
from app.services.email_service import send_treatment_notification


MAX_PHOTOS = 10


def update_anomaly_status(anomaly, user, new_status, comment="", photos=None):
    """Met à jour le statut d'une anomalie et notifie la prise en charge."""

    if not user or not user.is_active:
        raise AnomalyValidationError("Utilisateur introuvable ou désactivé.")

    if user.role not in {"ADMIN", "CHEF_SERVICE", "CHEF_SECTEUR"}:
        raise AnomalyValidationError(
            "Seuls les administrateurs, chefs de service et chefs de secteur peuvent traiter les anomalies."
        )

    locked_anomaly = (
        db.session.query(Anomaly)
        .filter(Anomaly.id == anomaly.id)
        .with_for_update()
        .populate_existing()
        .one_or_none()
    )

    if not locked_anomaly:
        raise AnomalyValidationError("Anomalie introuvable.")

    if not user_can_access_anomaly(user, locked_anomaly):
        raise AnomalyValidationError(
            "Vous n'êtes pas autorisé à traiter cette anomalie."
        )

    allowed_transitions = {
        "EN_ATTENTE": "EN_COURS_DE_TRAITEMENT",
        "EN_COURS_DE_TRAITEMENT": "TRAITEE",
    }

    old_status = locked_anomaly.status

    if new_status != allowed_transitions.get(old_status):
        raise ValueError(
            f"Transition interdite : {old_status} vers {new_status}."
        )

    photos = photos or []

    if new_status == "TRAITEE" and not photos:
        raise AnomalyValidationError(
            "Une photo après traitement est obligatoire pour clôturer l'anomalie."
        )

    if len(photos) > MAX_PHOTOS:
        raise AnomalyValidationError(
            f"Maximum {MAX_PHOTOS} photos autorisées."
        )

    if new_status == "EN_COURS_DE_TRAITEMENT" and photos:
        raise AnomalyValidationError(
            "Les photos après traitement sont acceptées uniquement à la clôture."
        )

    validated_photos = [
        (photo, validate_photo(photo))
        for photo in photos
    ]

    upload_folder = Path(
        current_app.config["UPLOAD_FOLDER"]
    ).resolve()

    anomaly_folder = upload_folder / "anomalies"
    anomaly_folder.mkdir(parents=True, exist_ok=True)

    saved_files = []
    notification_result = None
    action_at = datetime.now(timezone.utc)

    try:
        for photo, extension in validated_photos:
            filename = f"{uuid4().hex}{extension}"
            file_path = anomaly_folder / filename

            photo.stream.seek(0)
            photo.save(file_path)
            saved_files.append(file_path)

            db.session.add(
                AnomalyPhoto(
                    anomaly_id=locked_anomaly.id,
                    file_path=f"anomalies/{filename}",
                    photo_type="APRES",
                    uploaded_by=user.id,
                )
            )

        locked_anomaly.status = new_status

        if new_status == "TRAITEE":
            locked_anomaly.treated_at = action_at

        db.session.add(
            History(
                anomaly_id=locked_anomaly.id,
                user_id=user.id,
                old_status=old_status,
                new_status=new_status,
                comment=comment.strip() if isinstance(comment, str) else "",
                created_at=action_at,
            )
        )

        db.session.commit()

    except Exception:
        db.session.rollback()

        for file_path in saved_files:
            try:
                file_path.unlink(missing_ok=True)
            except OSError:
                current_app.logger.exception(
                    "Impossible de supprimer le fichier : %s",
                    file_path
                )

        raise

    # L'e-mail est envoyé APRÈS le commit :
    # un problème SMTP ne peut pas annuler la mise à jour
    # du statut ni l'historique.

    if (
        old_status == "EN_ATTENTE"
        and new_status == "EN_COURS_DE_TRAITEMENT"
    ):
        notification_result = send_treatment_notification(
            anomaly=locked_anomaly,
            handler=user,
            action_at=action_at,
        )

    locked_anomaly._email_notification_result = notification_result

    return locked_anomaly
