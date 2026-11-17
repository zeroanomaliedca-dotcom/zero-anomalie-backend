
from getpass import getpass

from run import app


def test_users():
    comptes = [
        ("admin", "ADMIN"),
        ("chef_agadir", "CHEF AGADIR"),
        ("chef_inzegane", "CHEF INZEGANE"),
        ("technicien1", "TECHNICIEN 1"),
    ]

    client = app.test_client()

    print("\n========== TEST API USERS ==========\n")

    for username, profil in comptes:
        print(f"\n--- {profil} ({username}) ---")

        password = getpass(f"Mot de passe de {username} : ")

        login_response = client.post(
            "/api/auth/login",
            json={
                "username": username,
                "password": password
            }
        )

        if login_response.status_code != 200:
            print("ECHEC CONNEXION :", login_response.status_code)
            continue

        token = login_response.get_json()["access_token"]

        response = client.get(
            "/api/users",
            headers={
                "Authorization": f"Bearer {token}"
            }
        )

        print("Code HTTP :", response.status_code)

        if response.status_code == 200:
            data = response.get_json()

            print("Nombre d'utilisateurs :", data["total"])

            for user in data["users"]:
                print(
                    user["username"],
                    "|",
                    user["full_name"],
                    "|",
                    user["role"],
                    "| Actif:",
                    user["is_active"],
                    "| Secteurs:",
                    ", ".join(user["sectors"])
                )

            print("ACCES ADMIN VALIDE")

        elif response.status_code == 403:
            print("ACCES REFUSE COMME PREVU")

        else:
            print("REPONSE :", response.get_json())

    print("\n========== FIN DES TESTS ==========")


if __name__ == "__main__":
    test_users()
