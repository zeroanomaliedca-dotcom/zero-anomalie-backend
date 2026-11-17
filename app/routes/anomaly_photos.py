
from pathlib import Path, PureWindowsPath

from flask import Blueprint, jsonify, current_app, send_file
from flask_jwt_extended import jwt_required

from app.extensions import db
from app.models import Anomaly, AnomalyPhoto

from app.services.permissions import (
    current_user,
    user_can_access_anomaly,
)


anomaly_photos_bp = Blueprint(
    "anomaly_photos",
    __name__,
    url_prefix="/api/anomaly-photos"
)


@anomaly_photos_bp.get("/<int:photo_id>")
@jwt_required()
def get_anomaly_photo(photo_id):
    """
    Affiche une photo après vérification des permissions.
    Les fichiers ne sont jamais accessibles publiquement.
    """

    # 1. Vérifier l'utilisateur connecté
    user = current_user()

    if not user:
        return jsonify({
            "status": "error",
            "message": "Utilisateur introuvable ou désactivé."
        }), 401

    # 2. Vérifier la photo
    photo = db.session.get(AnomalyPhoto, photo_id)

    if not photo:
        return jsonify({
            "status": "error",
            "message": "Photo introuvable."
        }), 404

    # 3. Vérifier l'anomalie associée
    anomaly = db.session.get(Anomaly, photo.anomaly_id)

    if not anomaly:
        return jsonify({
            "status": "error",
            "message": "Anomalie introuvable."
        }), 404

    # 4. Vérifier les autorisations
    if not user_can_access_anomaly(user, anomaly):
        return jsonify({
            "status": "error",
            "message": "Vous n'avez pas accès à cette photo."
        }), 403

    # 5. Vérifier et normaliser le chemin
    if not isinstance(photo.file_path, str) or not photo.file_path.strip():
        return jsonify({
            "status": "error",
            "message": "Chemin de fichier invalide."
        }), 400

    normalized_path = photo.file_path.replace("\\", "/")

    # Refuser les chemins absolus et les tentatives de traversée
    windows_path = PureWindowsPath(normalized_path)

    if (
        windows_path.is_absolute()
        or windows_path.drive
        or ".." in normalized_path.split("/")
        or normalized_path.startswith("/")
    ):
        return jsonify({
            "status": "error",
            "message": "Chemin de fichier invalide."
        }), 400

    # 6. Vérifier que le fichier reste dans UPLOAD_FOLDER
    upload_folder = Path(
        current_app.config["UPLOAD_FOLDER"]
    ).resolve()

    file_path = (
        upload_folder / normalized_path
    ).resolve()

    if not file_path.is_relative_to(upload_folder):
        return jsonify({
            "status": "error",
            "message": "Accès au chemin interdit."
        }), 400

    # 7. Vérifier l'existence du fichier
    if not file_path.is_file():
        return jsonify({
            "status": "error",
            "message": "Fichier photo introuvable sur le serveur."
        }), 404

    # 8. Envoyer la photo de manière sécurisée
    response = send_file(
        file_path,
        conditional=True,
        as_attachment=False,
        download_name=file_path.name,
    )

    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"

    return response
