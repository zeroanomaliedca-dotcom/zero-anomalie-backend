
from getpass import getpass

from app import create_app


PHOTOS = [1, 2]

ACCOUNTS = [
    ("technicien1", "Technicien déclarant", 200),
    ("chef_agadir", "Chef AGADIR", 200),
    ("chef_inzegane", "Chef INZEGANE", 403),
]


def main():
    app = create_app()

    print("\n=== TEST ACCES SECURISE AUX PHOTOS ===")

    with app.test_client() as client:

        for username, label, expected_status in ACCOUNTS:

            print(f"\n--- {label} ---")

            password = getpass(
                f"Mot de passe de {username} : "
            )

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

            for photo_id in PHOTOS:

                response = client.get(
                    f"/api/anomaly-photos/{photo_id}",
                    headers={
                        "Authorization": f"Bearer {token}"
                    },
                )

                print(
                    f"Photo {photo_id} | "
                    f"HTTP {response.status_code} | "
                    f"Type : {response.content_type} | "
                    f"Taille : {len(response.data)} octets"
                )

                if response.status_code == expected_status:
                    print("Résultat conforme.")
                else:
                    print(
                        "ATTENTION : résultat attendu :",
                        expected_status
                    )

    print("\n=== FIN DES TESTS ===")


if __name__ == "__main__":
    main()
