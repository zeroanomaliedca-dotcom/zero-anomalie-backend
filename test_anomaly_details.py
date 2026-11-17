
from getpass import getpass

from app import create_app


ANOMALY_ID = 1

ACCOUNTS = [
    ("technicien1", "Technicien déclarant"),
    ("chef_agadir", "Chef AGADIR"),
    ("chef_inzegane", "Chef INZEGANE"),
]


def main():
    app = create_app()

    print("\n=== TEST CONSULTATION DÉTAILLÉE ===")

    with app.test_client() as client:

        for username, label in ACCOUNTS:

            print(f"\n--- {label} ({username}) ---")
            password = getpass(f"Mot de passe de {username} : ")

            login = client.post(
                "/api/auth/login",
                json={
                    "username": username,
                    "password": password,
                },
            )

            if login.status_code != 200:
                print("Échec connexion :", login.status_code)
                continue

            token = login.get_json()["access_token"]

            response = client.get(
                f"/api/anomalies/{ANOMALY_ID}",
                headers={
                    "Authorization": f"Bearer {token}"
                },
            )

            print("Code HTTP :", response.status_code)

            result = response.get_json() or {}

            if response.status_code == 200:
                anomaly = result["anomaly"]

                print("Référence :", anomaly["reference"])
                print("Statut :", anomaly["status"])
                print("Secteur :", anomaly["sector"]["name"])
                print("Catégorie :", anomaly["category"]["name"])
                print("Technicien :", anomaly["technician"]["username"])

                print("\nPhotos :")
                for photo in anomaly["photos"]:
                    print(
                        photo["photo_type"],
                        "|",
                        photo["file_path"],
                        "|",
                        photo["uploaded_at"],
                    )

                print("\nHistorique :")
                for event in anomaly["history"]:
                    user = event["user"]
                    username_event = (
                        user["username"] if user else "Inconnu"
                    )

                    print(
                        event["old_status"],
                        "->",
                        event["new_status"],
                        "|",
                        username_event,
                        "|",
                        event["created_at"],
                    )

            else:
                print("Réponse :", result)

    print("\n=== FIN DES TESTS ===")


if __name__ == "__main__":
    main()
