
import uuid
from datetime import datetime, timezone
from pathlib import Path

from flask import current_app
from PIL import Image, UnidentifiedImageError

from app.extensions import db
from app.models import (
    User,
    Sector,
    Category,
    Anomaly,
    AnomalyPhoto,
    History,
)


MAX_PHOTOS_PER_DECLARATION = 10
MAX_PHOTO_SIZE = 5 * 1024 * 1024

ALLOWED_FORMATS = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "WEBP": ".webp",
    "GIF": ".gif",
    "BMP": ".bmp",
    "TIFF": ".tiff",
}

ALLOWED_DECLARATION_ROLES = {
    "ADMIN",
    "CHEF_SECTEUR",
    "TECHNICIEN",
}


class AnomalyValidationError(Exception):
    pass


def generate_reference():
    """Génère une référence unique."""
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    unique_part = uuid.uuid4().hex[:8].upper()

    return f"ZA-{date_part}-{unique_part}"


def validate_coordinates(latitude, longitude):
    """Valide les coordonnées GPS."""

    if latitude in (None, "") and longitude in (None, ""):
        return None, None

    if latitude in (None, "") or longitude in (None, ""):
        raise AnomalyValidationError(
            "La latitude et la longitude doivent être renseignées ensemble."
        )

    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError):
        raise AnomalyValidationError("Coordonnées GPS invalides.")

    if not -90 <= latitude <= 90:
        raise AnomalyValidationError("Latitude invalide.")

    if not -180 <= longitude <= 180:
        raise AnomalyValidationError("Longitude invalide.")

    return latitude, longitude


def validate_photo(photo):
    """Vérifie la taille et le véritable format de l'image."""

    if not photo or not photo.filename:
        raise AnomalyValidationError("Une photo est invalide.")

    photo.stream.seek(0, 2)
    file_size = photo.stream.tell()
    photo.stream.seek(0)

    if file_size == 0:
        raise AnomalyValidationError("Une photo est vide.")

    if file_size > MAX_PHOTO_SIZE:
        raise AnomalyValidationError(
            "Chaque photo ne doit pas dépasser 5 Mo."
        )

    try:
        with Image.open(photo.stream) as image:
            image.verify()
            image_format = image.format

    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
    ):
        raise AnomalyValidationError(
            "Le fichier envoyé n'est pas une image valide."
        )

    finally:
        photo.stream.seek(0)

    if image_format not in ALLOWED_FORMATS:
        raise AnomalyValidationError(
            "Format non autorisé. Utilisez JPG, JPEG, PNG, WEBP, GIF, BMP ou TIFF."
        )

    return ALLOWED_FORMATS[image_format]


def create_anomaly(
    technician_id,
    sector_id,
    category_id,
    title,
    description,
    declaration_method,
    latitude=None,
    longitude=None,
    location_address=None,
    photos=None,
):
    """Enregistre une anomalie et ses photos initiales.

    technician_id conserve son nom pour assurer la compatibilité
    avec les appels existants. Il représente désormais l'utilisateur
    qui déclare l'anomalie, quel que soit son rôle.
    """

    photos = photos or []

    if not isinstance(title, str) or not title.strip():
        raise AnomalyValidationError("Le titre est obligatoire.")

    if not isinstance(description, str) or not description.strip():
        raise AnomalyValidationError("La description est obligatoire.")

    if declaration_method not in {"SUR_PLACE", "PHOTO_RECUE"}:
        raise AnomalyValidationError("Méthode de déclaration invalide.")

    if not photos:
        raise AnomalyValidationError("Ajoutez au moins une photo.")

    if len(photos) > MAX_PHOTOS_PER_DECLARATION:
        raise AnomalyValidationError(
            f"Maximum {MAX_PHOTOS_PER_DECLARATION} photos par déclaration."
        )

    declarant = db.session.get(User, technician_id)

    if not declarant or not declarant.is_active:
        raise AnomalyValidationError(
            "Utilisateur introuvable ou désactivé."
        )

    if declarant.role not in ALLOWED_DECLARATION_ROLES:
        raise AnomalyValidationError(
            "Votre rôle ne permet pas de déclarer une anomalie."
        )

    sector = db.session.get(Sector, sector_id)

    if not sector or not sector.is_active:
        raise AnomalyValidationError(
            "Secteur invalide ou désactivé."
        )

    category = db.session.get(Category, category_id)

    if not category or not category.is_active:
        raise AnomalyValidationError(
            "Catégorie invalide ou désactivée."
        )

    latitude, longitude = validate_coordinates(
        latitude,
        longitude
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

    anomaly = Anomaly(
        reference=generate_reference(),
        title=title.strip(),
        description=description.strip(),
        declaration_method=declaration_method,
        status="EN_ATTENTE",
        sector_id=sector.id,
        category_id=category.id,
        technician_id=declarant.id,
        latitude=latitude,
        longitude=longitude,
        location_address=(
            location_address.strip()
            if isinstance(location_address, str)
            and location_address.strip()
            else None
        ),
        created_at=datetime.now(timezone.utc),
    )

    saved_files = []

    try:
        db.session.add(anomaly)
        db.session.flush()

        for photo, extension in validated_photos:
            filename = f"{uuid.uuid4().hex}{extension}"
            destination = anomaly_folder / filename

            photo.save(destination)
            saved_files.append(destination)

            relative_path = f"anomalies/{filename}"

            db.session.add(
                AnomalyPhoto(
                    anomaly_id=anomaly.id,
                    file_path=relative_path,
                    photo_type="AVANT",
                    uploaded_by=declarant.id,
                )
            )

        db.session.add(
            History(
                anomaly_id=anomaly.id,
                user_id=declarant.id,
                old_status=None,
                new_status="EN_ATTENTE",
                comment="Création de la déclaration.",
            )
        )

        db.session.commit()

        return anomaly

    except Exception:
        db.session.rollback()

        for file_path in saved_files:
            try:
                file_path.unlink(missing_ok=True)
            except OSError:
                current_app.logger.exception(
                    "Impossible de supprimer le fichier %s",
                    file_path
                )

        raise
