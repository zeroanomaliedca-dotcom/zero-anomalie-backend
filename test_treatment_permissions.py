
from getpass import getpass
from io import BytesIO

from PIL import Image

from app import create_app


ANOMALY_ID = 1
USERNAME = "chef_agadir"


def main():
    app = create_app()
    password = getpass("Mot de passe du chef AGADIR : ")

    # Création d'une image JPG de test
    image_buffer = BytesIO()
    image = Image.new("RGB", (800, 600), "white")
    image.save(image_buffer, format="JPEG", quality=90)
    image_buffer.seek(0)

    with app.test_client() as client:

        login = client.post(
            "/api/auth/login",
            json={
                "username": USERNAME,
                "password": password,
            },
        )

        if login.status_code != 200:
            print("Échec authentification :", login.status_code)
            return

        token = login.get_json()["access_token"]

        response = client.patch(
            f"/api/anomalies/{ANOMALY_ID}/status",
            headers={
                "Authorization": f"Bearer {token}"
            },
            data={
                "new_status": "TRAITEE",
                "comment": "Anomalie traitée. Photo de contrôle jointe.",
                "photos": [
                    (image_buffer, "photo_traitement.jpg")
                ],
            },
            content_type="multipart/form-data",
        )

        print("\nCode HTTP :", response.status_code)
        print("Réponse :", response.get_json())

        if response.status_code == 200:
            print("\nSUCCÈS : anomalie clôturée avec une photo JPG.")
        else:
            print("\nÉCHEC : vérifier le message retourné.")


if __name__ == "__main__":
    main()
