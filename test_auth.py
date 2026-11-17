
from getpass import getpass

from app import create_app


app = create_app()

username = input("Identifiant : ").strip()
password = getpass("Mot de passe : ")

with app.test_client() as client:
    response = client.post(
        "/api/auth/login",
        json={
            "username": username,
            "password": password
        }
    )

    print("\nCode HTTP connexion :", response.status_code)

    result = response.get_json() or {}

    if response.status_code == 200:
        print("Connexion réussie.")
        print("Utilisateur :", result["user"]["username"])
        print("Rôle :", result["user"]["role"])

        token = result["access_token"]

        profile_response = client.get(
            "/api/auth/me",
            headers={
                "Authorization": f"Bearer {token}"
            }
        )

        print("\nCode HTTP profil :", profile_response.status_code)

        if profile_response.status_code == 200:
            profile = profile_response.get_json()
            print("Profil récupéré avec succès.")
            print("Permissions :", profile["permissions"])
        else:
            print("Erreur lors de la récupération du profil.")

    else:
        print("Échec de connexion :", result.get("message"))
