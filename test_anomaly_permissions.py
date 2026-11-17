
from getpass import getpass

from app import create_app
from app.models import Sector, Category


app = create_app()


def login(client, username):
    password = getpass(f"Mot de passe de {username} : ")

    response = client.post(
        "/api/auth/login",
        json={
            "username": username,
            "password": password,
        },
    )

    if response.status_code != 200:
        print(f"Connexion impossible pour {username}.")
        return None

    return response.get_json()["access_token"]


with app.app_context():
    sectors = {
        sector.name: sector.id
        for sector in Sector.query.filter_by(is_active=True).all()
    }

    category = Category.query.filter_by(is_active=True).first()

    if not category:
        raise RuntimeError("Aucune catégorie active dans la base.")

    print("Secteurs :", sectors)
    print("Catégorie de test :", category.name)

    with app.test_client() as client:
        technician_token = login(client, "technicien1")

        if technician_token:
            headers = {
                "Authorization": f"Bearer {technician_token}"
            }

            print("\n--- Test déclaration AGADIR ---")
            response = client.post(
                "/api/anomalies",
                headers=headers,
                data={
                    "sector_id": str(sectors["AGADIR"]),
                    "category_id": str(category.id),
                    "title": "TEST AUTORISATION",
                    "description": "Test sans création d'anomalie.",
                    "declaration_method": "SUR_PLACE",
                },
            )
            print("Code HTTP attendu : 400 (photo obligatoire)")
            print("Code HTTP obtenu :", response.status_code)
            print("Réponse :", response.get_json())

            print("\n--- Test déclaration INZEGANE ---")
            response = client.post(
                "/api/anomalies",
                headers=headers,
                data={
                    "sector_id": str(sectors["INZEGANE"]),
                    "category_id": str(category.id),
                    "title": "TEST AUTORISATION",
                    "description": "Test sans création d'anomalie.",
                    "declaration_method": "SUR_PLACE",
                },
            )
            print("Code HTTP attendu : 400 (photo obligatoire)")
            print("Code HTTP obtenu :", response.status_code)
            print("Réponse :", response.get_json())

        print("\n--- Test accès chef à l'API technicien ---")
        chef_token = login(client, "chef_agadir")

        if chef_token:
            response = client.post(
                "/api/anomalies",
                headers={
                    "Authorization": f"Bearer {chef_token}"
                },
                data={},
            )
            print("Code HTTP attendu : 403")
            print("Code HTTP obtenu :", response.status_code)
            print("Réponse :", response.get_json())
