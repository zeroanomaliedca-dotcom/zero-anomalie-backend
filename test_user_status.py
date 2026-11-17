
from getpass import getpass

from run import app


def test_user_status():
    client = app.test_client()

    print("\n========== TEST ACTIVATION / DESACTIVATION ==========\n")

    # Connexion ADMIN
    admin_password = getpass("Mot de passe ADMIN : ")

    login = client.post(
        "/api/auth/login",
        json={
            "username": "admin",
            "password": admin_password
        }
    )

    if login.status_code != 200:
        print("ECHEC CONNEXION ADMIN")
        return

    token = login.get_json()["access_token"]

    headers = {
        "Authorization": f"Bearer {token}"
    }

    user_id = 6

    # 1. Désactiver le technicien
    print("\n--- DESACTIVATION TECHNICIEN ID 6 ---")

    response = client.patch(
        f"/api/users/{user_id}/status",
        json={"is_active": False},
        headers=headers
    )

    print("Code HTTP :", response.status_code)
    print("Réponse :", response.get_json())

    # 2. Vérifier que le technicien ne peut plus se connecter
    print("\n--- TEST CONNEXION COMPTE DESACTIVE ---")

    technician_password = getpass(
        "Mot de passe du technicien_test_api : "
    )

    response = client.post(
        "/api/auth/login",
        json={
            "username": "technicien_test_api",
            "password": technician_password
        }
    )

    print("Code HTTP :", response.status_code)
    print("Réponse :", response.get_json())

    # 3. Réactiver le technicien
    print("\n--- REACTIVATION TECHNICIEN ID 6 ---")

    response = client.patch(
        f"/api/users/{user_id}/status",
        json={"is_active": True},
        headers=headers
    )

    print("Code HTTP :", response.status_code)
    print("Réponse :", response.get_json())

    # 4. Vérifier que le technicien peut se reconnecter
    print("\n--- TEST CONNEXION APRES REACTIVATION ---")

    response = client.post(
        "/api/auth/login",
        json={
            "username": "technicien_test_api",
            "password": technician_password
        }
    )

    print("Code HTTP :", response.status_code)

    if response.status_code == 200:
        print("CONNEXION REUSSIE")
    else:
        print("CONNEXION REFUSEE :", response.get_json())

    # 5. Vérifier la protection du compte ADMIN
    print("\n--- PROTECTION COMPTE ADMIN ---")

    response = client.patch(
        "/api/users/1/status",
        json={"is_active": False},
        headers=headers
    )

    print("Code HTTP :", response.status_code)
    print("Réponse :", response.get_json())

    print("\n========== FIN DES TESTS ==========")


if __name__ == "__main__":
    test_user_status()
