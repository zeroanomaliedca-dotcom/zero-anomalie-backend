
from getpass import getpass
from pathlib import Path

from app import create_app
from app.extensions import db
from app.models import (
    User,
    Sector,
    Category,
    Anomaly,
    AnomalyPhoto,
    History,
)


app = create_app()

REFERENCE = "ZA-20261112-38A54DBB"


def login(client, username):
    password = getpass(f"Mot de passe de {username} : ")

    response = client.post(
        "/api/auth/login",
        json={
            "username": username,
            "password": password,
        },
    )

    if response.status_code != 200:
        raise RuntimeError(f"Connexion impossible : {username}")

    return response.get_json()["access_token"]


with app.app_context():

    print("\n================================")
    print("VERIFICATION DE L'ANOMALIE")
    print("================================")

    anomaly = Anomaly.query.filter_by(
        reference=REFERENCE
    ).first()

    if not anomaly:
        raise RuntimeError(
            f"Anomalie introuvable : {REFERENCE}"
        )

    technician = db.session.get(
        User,
        anomaly.technician_id
    )

    sector = db.session.get(
        Sector,
        anomaly.sector_id
    )

    category = db.session.get(
        Category,
        anomaly.category_id
    )

    print("Référence :", anomaly.reference)
    print("Statut :", anomaly.status)
    print("Technicien :", technician.username if technician else "Introuvable")
    print("Nom complet :", technician.full_name if technician else "Introuvable")
    print("Secteur :", sector.name if sector else "Introuvable")
    print("Catégorie :", category.name if category else "Introuvable")
    print("Date de déclaration :", anomaly.created_at)

    print("\n================================")
    print("VERIFICATION DES PHOTOS")
    print("================================")

    upload_folder = Path(app.config["UPLOAD_FOLDER"])

    photos = AnomalyPhoto.query.filter_by(
        anomaly_id=anomaly.id
    ).all()

    print("Nombre de photos :", len(photos))

    for photo in photos:
        photo_path = upload_folder / photo.file_path

        print("Type :", photo.photo_type)
        print("Chemin :", photo.file_path)
        print("Fichier présent :", photo_path.is_file())
        print("Déclarant :", photo.uploaded_by)

    print("\n================================")
    print("VERIFICATION DE L'HISTORIQUE")
    print("================================")

    histories = History.query.filter_by(
        anomaly_id=anomaly.id
    ).order_by(History.created_at.asc()).all()

    print("Nombre d'entrées :", len(histories))

    for history in histories:
        history_user = db.session.get(
            User,
            history.user_id
        )

        print("Utilisateur :", history_user.username if history_user else "Inconnu")
        print("Ancien statut :", history.old_status)
        print("Nouveau statut :", history.new_status)
        print("Commentaire :", history.comment)
        print("Date :", history.created_at)
        print("----------------------------")

    print("\n================================")
    print("VERIFICATION DES AUTORISATIONS")
    print("================================")

    accounts = [
        "admin",
        "chef_agadir",
        "chef_inzegane",
        "technicien1",
        "technicien2",
    ]

    with app.test_client() as client:

        for username in accounts:

            token = login(client, username)

            response = client.get(
                "/api/anomalies",
                headers={
                    "Authorization": f"Bearer {token}"
                },
            )

            print(f"\nCompte : {username}")
            print("Code HTTP :", response.status_code)

            if response.status_code != 200:
                print("Erreur :", response.get_json())
                continue

            result = response.get_json() or {}

            visible = any(
                item.get("reference") == REFERENCE
                for item in result.get("anomalies", [])
            )

            print(
                "Anomalie :",
                "VISIBLE" if visible else "NON VISIBLE"
            )

    print("\n================================")
    print("VERIFICATION TERMINEE")
    print("================================")
