
from getpass import getpass

from run import app


def test_dashboard():
    comptes = [
        ("admin", "ADMIN"),
        ("chef_agadir", "CHEF AGADIR"),
        ("chef_inzegane", "CHEF INZEGANE"),
        ("technicien1", "TECHNICIEN 1"),
        ("technicien2", "TECHNICIEN 2"),
    ]

    client = app.test_client()

    print("\n========== TEST API DASHBOARD ==========\n")

    for username, profil in comptes:
        print(f"\n--- {profil} ({username}) ---")

        password = getpass(f"Mot de passe de {username} : ")

        # Connexion
        login_response = client.post(
            "/api/auth/login",
            json={
                "username": username,
                "password": password
            }
        )

        if login_response.status_code != 200:
            print("ECHEC CONNEXION :", login_response.status_code)
            print(login_response.get_json())
            continue

        token = login_response.get_json()["access_token"]

        # Consultation du Dashboard
        dashboard_response = client.get(
            "/api/dashboard",
            headers={
                "Authorization": f"Bearer {token}"
            }
        )

        print("Code HTTP :", dashboard_response.status_code)

        if dashboard_response.status_code == 200:
            data = dashboard_response.get_json()["dashboard"]

            print("Nombre total :", data["total"])
            print("En attente :", data["statuses"]["EN_ATTENTE"])
            print(
                "En cours :",
                data["statuses"]["EN_COURS_DE_TRAITEMENT"]
            )
            print("Traitées :", data["statuses"]["TRAITEE"])
            print("Taux de traitement :", data["treatment_rate"], "%")

            print("\nRépartition par secteur :")
            for secteur in data["by_sector"]:
                print(
                    secteur["sector_name"],
                    ":", secteur["count"]
                )

            print("\nRépartition par catégorie :")
            for categorie in data["by_category"]:
                print(
                    categorie["category_name"],
                    ":", categorie["count"]
                )

            print("\nTEST REUSSI")

        else:
            print("ERREUR DASHBOARD :", dashboard_response.get_json())

    print("\n========== FIN DES TESTS ==========")


if __name__ == "__main__":
    test_dashboard()
