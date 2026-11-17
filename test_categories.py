
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
        print(f"Connexion échouée pour {username}:")
        print(response.get_json())
        return None

    token = response.get_json()["access_token"]

    return {
        "Authorization": f"Bearer {token}"
    }


def test_categories():
    client = app.test_client()

    print("\n========== TEST GESTION DES CATEGORIES ==========\n")

    # Connexion ADMIN
    admin_password = getpass("Mot de passe ADMIN : ")
    admin_headers = login(client, "admin", admin_password)

    if not admin_headers:
        return

    # 1. Liste des catégories
    print("\n--- 1. LISTE DES CATEGORIES ---")

    response = client.get(
        "/api/categories",
        headers=admin_headers
    )

    print("HTTP :", response.status_code)
    print(response.get_json())

    # 2. Création
    category_name = (
        "Categorie Test "
        + datetime.now().strftime("%Y%m%d%H%M%S")
    )

    print("\n--- 2. CREATION D'UNE CATEGORIE ---")

    response = client.post(
        "/api/categories",
        headers=admin_headers,
        json={
            "name": category_name,
            "description": "Catégorie créée pour tester l'API."
        }
    )

    print("HTTP :", response.status_code)
    print(response.get_json())

    if response.status_code != 201:
        print("ECHEC CREATION")
        return

    category_id = response.get_json()["category"]["id"]

    # 3. Modification
    print("\n--- 3. MODIFICATION DE LA CATEGORIE ---")

    response = client.put(
        f"/api/categories/{category_id}",
        headers=admin_headers,
        json={
            "name": category_name + " Modifie",
            "description": "Description modifiée."
        }
    )

    print("HTTP :", response.status_code)
    print(response.get_json())

    # 4. Désactivation
    print("\n--- 4. DESACTIVATION DE LA CATEGORIE ---")

    response = client.patch(
        f"/api/categories/{category_id}/status",
        headers=admin_headers,
        json={
            "is_active": False
        }
    )

    print("HTTP :", response.status_code)
    print(response.get_json())

    # 5. Vérification des droits technicien
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
            "/api/categories",
            headers=technician_headers
        )

        print("Consultation HTTP :", response.status_code)

        response = client.post(
            "/api/categories",
            headers=technician_headers,
            json={
                "name": "Categorie interdite"
            }
        )

        print("Création HTTP :", response.status_code)
        print(response.get_json())

    print("\n========== FIN DES TESTS ==========\n")


if __name__ == "__main__":
    test_categories()
