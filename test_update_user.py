
from getpass import getpass

from run import app


def test_update_user():
    client = app.test_client()

    print("\n========== TEST MODIFICATION UTILISATEUR ==========\n")

    password_admin = getpass("Mot de passe ADMIN : ")

    login = client.post(
        "/api/auth/login",
        json={
            "username": "admin",
            "password": password_admin
        }
    )

    if login.status_code != 200:
        print("ECHEC CONNEXION ADMIN")
        return

    token = login.get_json()["access_token"]

    headers = {
        "Authorization": f"Bearer {token}"
    }

    # 1. Modifier le nom complet du technicien de test (ID 6)
    print("\n--- MODIFICATION TECHNICIEN ID 6 ---")

    response = client.put(
        "/api/users/6",
        json={
            "full_name": "Technicien Test API Modifie"
        },
        headers=headers
    )

    print("Code HTTP :", response.status_code)
    print("Réponse :", response.get_json())

    # 2. Modifier les secteurs du chef de test (ID 7)
    print("\n--- MODIFICATION SECTEURS CHEF ID 7 ---")

    response = client.put(
        "/api/users/7",
        json={
            "full_name": "Chef Test API Modifie",
            "sector_ids": [1, 2, 3]
        },
        headers=headers
    )

    print("Code HTTP :", response.status_code)
    print("Réponse :", response.get_json())

    # 3. Vérifier le refus de modification du compte ADMIN (ID 1)
    print("\n--- PROTECTION COMPTE ADMIN ---")

    response = client.put(
        "/api/users/1",
        json={
            "full_name": "Administrateur Modifie"
        },
        headers=headers
    )

    print("Code HTTP :", response.status_code)
    print("Réponse :", response.get_json())

    # 4. Vérifier un utilisateur inexistant
    print("\n--- UTILISATEUR INEXISTANT ---")

    response = client.put(
        "/api/users/9999",
        json={
            "full_name": "Utilisateur Inexistant"
        },
        headers=headers
    )

    print("Code HTTP :", response.status_code)
    print("Réponse :", response.get_json())

    print("\n========== FIN DES TESTS ==========")


if __name__ == "__main__":
    test_update_user()
