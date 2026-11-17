
import json
from pathlib import Path
from getpass import getpass
from datetime import datetime
from io import BytesIO
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from pptx import Presentation


BASE_URL = "http://127.0.0.1:5000"
EXPORT_DIR = Path(__file__).resolve().parent / "exports"

# Secteurs actifs existants dans la base de test :
# 1 = AGADIR, 2 = INZEGANE, 3 = AIT MELLOUL
ACTIVE_SECTOR_IDS = [1, 2, 3]


def api_request(path, method="GET", data=None, token=None):
    headers = {}

    if data is not None:
        headers["Content-Type"] = "application/json"

    if token:
        headers["Authorization"] = f"Bearer {token}"

    body = json.dumps(data).encode("utf-8") if data is not None else None

    req = Request(
        BASE_URL + path,
        data=body,
        headers=headers,
        method=method
    )

    try:
        with urlopen(req, timeout=120) as response:
            return response.status, response.read()

    except HTTPError as error:
        return error.code, error.read()

    except URLError as error:
        raise RuntimeError(
            "Serveur Flask inaccessible. Vérifiez que python run.py est lancé."
        ) from error


def login(role_label):
    print(f"\n--- CONNEXION {role_label} ---")
    username = input("Identifiant : ").strip()
    password = getpass("Mot de passe : ")

    status, response = api_request(
        "/api/auth/login",
        method="POST",
        data={"username": username, "password": password}
    )

    if status != 200:
        print(f"ÉCHEC CONNEXION ({status})")
        print(response.decode("utf-8", errors="replace"))
        return None

    result = json.loads(response.decode("utf-8"))
    user = result.get("user", {})

    print("Connecté :", user.get("full_name"))
    print("Rôle :", user.get("role"))

    return {
        "token": result["access_token"],
        "user": user
    }


def export_test(label, token, start_date, end_date, sector_ids=None):
    payload = {
        "start_date": start_date,
        "end_date": end_date
    }

    if sector_ids is not None:
        payload["sector_ids"] = sector_ids

    print(f"\nTest : {label}")

    status, response = api_request(
        "/api/reports/powerpoint",
        method="POST",
        data=payload,
        token=token
    )

    if status == 200:
        try:
            presentation = Presentation(BytesIO(response))
        except Exception as error:
            print("ÉCHEC : fichier PowerPoint illisible :", error)
            return False

        EXPORT_DIR.mkdir(parents=True, exist_ok=True)

        suffix = label.lower().replace(" ", "_")
        filename = (
            f"test_{suffix}_{start_date.replace('-', '')}_"
            f"{end_date.replace('-', '')}.pptx"
        )

        output_path = EXPORT_DIR / filename
        output_path.write_bytes(response)

        print("RÉSULTAT : SUCCÈS")
        print("HTTP :", status)
        print("Diapositives :", len(presentation.slides))
        print("Fichier :", output_path)
        return True

    print("HTTP :", status)
    print(response.decode("utf-8", errors="replace"))

    return status == 403


def main():
    print("\n===== TEST DES PERMISSIONS EXPORT POWERPOINT =====")

    start_date = input("\nDate de début (AAAA-MM-JJ) : ").strip()
    end_date = input("Date de fin (AAAA-MM-JJ) : ").strip()

    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        print("Format de date invalide.")
        return

    if end < start:
        print("La date de fin doit être après la date de début.")
        return

    results = {}

    # 1. ADMIN : tous les secteurs, puis sélection d'AGADIR.
    admin = login("ADMIN")
    if not admin:
        print("Test ADMIN impossible.")
        return

    if admin["user"].get("role") != "ADMIN":
        print("ERREUR : ce compte n'est pas ADMIN.")
        return

    results["ADMIN - tous les secteurs"] = export_test(
        "ADMIN tous secteurs",
        admin["token"],
        start_date,
        end_date
    )

    results["ADMIN - secteur AGADIR"] = export_test(
        "ADMIN secteur AGADIR",
        admin["token"],
        start_date,
        end_date,
        [1]
    )

    # 2. CHEF : secteurs attribués uniquement.
    chef = login("CHEF_SECTEUR")
    if not chef:
        print("Test CHEF impossible.")
        return

    if chef["user"].get("role") != "CHEF_SECTEUR":
        print("ERREUR : ce compte n'est pas CHEF_SECTEUR.")
        return

    chef_sector_ids = chef["user"].get("sector_ids", [])

    if not chef_sector_ids:
        print("ERREUR : ce chef n'a aucun secteur attribué.")
        return

    results["CHEF - secteurs attribués"] = export_test(
        "CHEF secteurs attribues",
        chef["token"],
        start_date,
        end_date
    )

    # Vérifier qu'un chef ne peut pas exporter un autre secteur.
    forbidden_sectors = [
        sector_id for sector_id in ACTIVE_SECTOR_IDS
        if sector_id not in chef_sector_ids
    ]

    if forbidden_sectors:
        forbidden_id = forbidden_sectors[0]

        results["CHEF - secteur interdit"] = export_test(
            "CHEF secteur interdit",
            chef["token"],
            start_date,
            end_date,
            [forbidden_id]
        )
    else:
        print(
            "\nTEST CHEF - secteur interdit : NON EFFECTUÉ. "
            "Ce compte possède déjà tous les secteurs actifs."
        )

    # 3. TECHNICIEN : export interdit.
    technician = login("TECHNICIEN")
    if not technician:
        print("Test TECHNICIEN impossible.")
        return

    if technician["user"].get("role") != "TECHNICIEN":
        print("ERREUR : ce compte n'est pas TECHNICIEN.")
        return

    results["TECHNICIEN - export interdit"] = export_test(
        "TECHNICIEN export interdit",
        technician["token"],
        start_date,
        end_date
    )

    print("\n========== RÉCAPITULATIF ==========")
    for label, success in results.items():
        print(
            ("OK      " if success else "ÉCHEC   ") + label
        )

    if all(results.values()):
        print("\nTOUS LES TESTS EFFECTUÉS SONT RÉUSSIS.")
    else:
        print("\nAU MOINS UN TEST A ÉCHOUÉ. Vérification nécessaire.")


if __name__ == "__main__":
    main()
