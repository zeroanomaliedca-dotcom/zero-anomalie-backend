
from getpass import getpass

from run import app


def test_create_user():
    client = app.test_client()

    print("\n========== TEST CREATION UTILISATEURS ==========\n")

    # Connexion administrateur
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

    # Création d'un technicien de test
    print("\n--- CREATION TECHNICIEN ---")

    password_technicien = getpass(
        "Choisir un mot de passe de test (12 caractères minimum) : "
    )

    technicien_data = {
        "username": "technicien_test_api",
        "full_name": "Technicien Test API",
        "password": password_technicien,
        "role": "TECHNICIEN",
        "sector_ids": []
    }

    response = client.post(
        "/api/users",
        json=technicien_data,
        headers=headers
    )

    print("Code HTTP :", response.status_code)
    print("Réponse :", response.get_json())

    # Création d'un chef affecté à INZEGANE et AIT MELLOUL
    print("\n--- CREATION CHEF ---")

    password_chef = getpass(
        "Choisir un mot de passe de test pour le chef : "
    )

    chef_data = {
        "username": "chef_test_api",
        "full_name": "Chef Test API",
        "password": password_chef,
        "role": "CHEF_SECTEUR",
        "sector_ids": [2, 3]
    }

    response = client.post(
        "/api/users",
        json=chef_data,
        headers=headers
    )

    print("Code HTTP :", response.status_code)
    print("Réponse :", response.get_json())

    # Vérification : impossible de créer un administrateur
    print("\n--- TEST INTERDICTION CREATION ADMIN ---")

    admin_data = {
        "username": "admin_test_interdit",
        "full_name": "Admin Test Interdit",
        "password": "MotDePasseTest2026!",
        "role": "ADMIN",
        "sector_ids": []
    }

    response = client.post(
        "/api/users",
        json=admin_data,
        headers=headers
    )

    print("Code HTTP :", response.status_code)
    print("Réponse :", response.get_json())

    print("\n========== FIN DES TESTS ==========")


if __name__ == "__main__":
    test_create_user()
