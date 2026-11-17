
from getpass import getpass

from app import create_app


app = create_app()

ACCOUNTS = [
    "admin",
    "chef_agadir",
    "chef_inzegane",
    "technicien1",
    "technicien2",
]

with app.test_client() as client:
    for username in ACCOUNTS:
        password = getpass(f"Mot de passe de {username} : ")

        login_response = client.post(
            "/api/auth/login",
            json={
                "username": username,
                "password": password,
            },
        )

        if login_response.status_code != 200:
            print(f"\n{username} : ECHEC CONNEXION")
            continue

        token = login_response.get_json()["access_token"]

        response = client.get(
            "/api/anomalies",
            headers={"Authorization": f"Bearer {token}"},
        )

        print(f"\n--- {username} ---")
        print("Code HTTP :", response.status_code)

        result = response.get_json() or {}

        print("Nombre d'anomalies :", result.get("count"))
        print("Statut :", result.get("status"))

        if username.startswith("chef_"):
            print("Secteurs autorisés selon le compte :", username)

        if username.startswith("technicien"):
            mine_response = client.get(
                "/api/anomalies/mine",
                headers={"Authorization": f"Bearer {token}"},
            )
            print("Route /mine :", mine_response.status_code)
