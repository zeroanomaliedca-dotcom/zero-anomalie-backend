
from getpass import getpass
from datetime import datetime

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
        print(f"Connexion échouée : {username}")
        print(response.get_json())
        return None

    token = response.get_json()["access_token"]

    return {
        "Authorization": f"Bearer {token}"
    }


def test_sectors():
    client = app.test_client()

    print("\n========== TEST GESTION DES SECTEURS ==========\n")

    # Connexion ADMIN
    admin_password = getpass("Mot de passe ADMIN : ")
    admin_headers = login(client, "admin", admin_password)

    if not admin_headers:
        return

    # 1. Consultation
    print("\n--- 1. LISTE DES SECTEURS ---")

    response = client.get(
        "/api/sectors",
        headers=admin_headers
    )

    print("HTTP :", response.status_code)
    print(response.get_json())

    # 2. Création
    sector_name = (
        "SECTEUR TEST "
        + datetime.now().strftime("%Y%m%d%H%M%S")
    )

    print("\n--- 2. CREATION D'UN SECTEUR ---")

    response = client.post(
        "/api/sectors",
        headers=admin_headers,
        json={
            "name": sector_name
        }
    )

    print("HTTP :", response.status_code)
    print(response.get_json())

    if response.status_code != 201:
        print("ECHEC CREATION")
        return

    sector_id = response.get_json()["sector"]["id"]

    # 3. Modification
    print("\n--- 3. MODIFICATION DU SECTEUR ---")

    response = client.put(
        f"/api/sectors/{sector_id}",
        headers=admin_headers,
        json={
            "name": sector_name + " MODIFIE"
        }
    )

    print("HTTP :", response.status_code)
    print(response.get_json())

    # 4. Désactivation
    print("\n--- 4. DESACTIVATION DU SECTEUR ---")

    response = client.patch(
        f"/api/sectors/{sector_id}/status",
        headers=admin_headers,
        json={
            "is_active": False
        }
    )

    print("HTTP :", response.status_code)
    print(response.get_json())

    # 5. Vérification technicien
    print("\n--- 5. TEST DES DROITS TECHNICIEN ---")

    technician_password = getpass(
        "Mot de passe technicien1 : "
    )

    technician_headers = login(
        client,
        "technicien1",
        technician_password
    )

    if technician_headers:
        response = client.get(
            "/api/sectors",
            headers=technician_headers
        )

        print("Consultation HTTP :", response.status_code)
        print(response.get_json())

        response = client.post(
            "/api/sectors",
            headers=technician_headers,
            json={
                "name": "SECTEUR INTERDIT"
            }
        )

        print("Création HTTP :", response.status_code)
        print(response.get_json())

    print("\n========== FIN DES TESTS ==========\n")


if __name__ == "__main__":
    test_sectors()
