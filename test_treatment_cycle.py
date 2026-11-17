
from getpass import getpass
from io import BytesIO

from PIL import Image

from run import app


def login(client, username, password):
    response = client.post(
        "/api/auth/login",
        json={
            "username": username,
            "password": password
        }
    )

    if response.status_code != 200:
        print("ECHEC CONNEXION :", username)
        print(response.get_json())
        return None

    return {
        "Authorization": (
            "Bearer " + response.get_json()["access_token"]
        )
    }


def create_test_image():
    image = Image.new("RGB", (200, 200), "white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def test_treatment_cycle():
    client = app.test_client()

    print("\n========== TEST COMPLET DU TRAITEMENT ==========\n")

    technician_password = getpass("Mot de passe technicien1 : ")
    chef_password = getpass("Mot de passe chef_agadir : ")

    technician_headers = login(
        client, "technicien1", technician_password
    )

    chef_headers = login(
        client, "chef_agadir", chef_password
    )

    if not technician_headers or not chef_headers:
        return

    # 1. Création d'une anomalie de test
    print("\n--- 1. CREATION DE L'ANOMALIE ---")

    response = client.post(
        "/api/anomalies",
        headers=technician_headers,
        data={
            "title": "TEST CYCLE TRAITEMENT",
            "description": "Anomalie créée pour tester le cycle complet.",
            "declaration_method": "SUR_PLACE",
            "sector_id": "1",
            "category_id": "1",
            "photos": (
                create_test_image(),
                "photo_avant.png"
            )
        },
        content_type="multipart/form-data"
    )

    print("HTTP :", response.status_code)
    print(response.get_json())

    if response.status_code != 201:
        print("ECHEC CREATION. Arrêt du test.")
        return

    anomaly_id = response.get_json()["anomaly"]["id"]

    print("ID ANOMALIE :", anomaly_id)

    # 2. Tentative de clôture directe
    print("\n--- 2. CLOTURE DIRECTE INTERDITE ---")

    response = client.patch(
        f"/api/anomalies/{anomaly_id}/status",
        headers=chef_headers,
        data={
            "new_status": "TRAITEE"
        },
        content_type="multipart/form-data"
    )

    print("HTTP :", response.status_code)
    print(response.get_json())

    # 3. Début du traitement
    print("\n--- 3. DEBUT DU TRAITEMENT ---")

    response = client.patch(
        f"/api/anomalies/{anomaly_id}/status",
        headers=chef_headers,
        data={
            "new_status": "EN_COURS_DE_TRAITEMENT"
        },
        content_type="multipart/form-data"
    )

    print("HTTP :", response.status_code)
    print(response.get_json())

    if response.status_code != 200:
        print("ECHEC DEBUT TRAITEMENT. Arrêt du test.")
        return

    # 4. Clôture sans photo
    print("\n--- 4. CLOTURE SANS PHOTO INTERDITE ---")

    response = client.patch(
        f"/api/anomalies/{anomaly_id}/status",
        headers=chef_headers,
        data={
            "new_status": "TRAITEE"
        },
        content_type="multipart/form-data"
    )

    print("HTTP :", response.status_code)
    print(response.get_json())

    # 5. Clôture avec photo après traitement
    print("\n--- 5. CLOTURE AVEC PHOTO APRES ---")

    response = client.patch(
        f"/api/anomalies/{anomaly_id}/status",
        headers=chef_headers,
        data={
            "new_status": "TRAITEE",
            "comment": "Intervention réalisée. Test de validation."
            ,
            "photos": (
                create_test_image(),
                "photo_apres.png"
            )
        },
        content_type="multipart/form-data"
    )

    print("HTTP :", response.status_code)
    print(response.get_json())

    # 6. Vérification du détail, des photos et de l'historique
    print("\n--- 6. VERIFICATION FINALE ---")

    response = client.get(
        f"/api/anomalies/{anomaly_id}",
        headers=chef_headers
    )

    print("HTTP :", response.status_code)

    if response.status_code == 200:
        anomaly = response.get_json()["anomaly"]

        print("REFERENCE :", anomaly.get("reference"))
        print("STATUT :", anomaly.get("status"))
        print("PHOTOS :")

        for photo in anomaly.get("photos", []):
            print(
                photo.get("photo_type"),
                photo.get("file_path")
            )

        print("HISTORIQUE :")

        for event in anomaly.get("history", []):
            print(
                event.get("old_status"),
                "->",
                event.get("new_status"),
                "|",
                event.get("comment")
            )

    print("\n========== FIN DU TEST ==========\n")


if __name__ == "__main__":
    test_treatment_cycle()
