
import json
from pathlib import Path
from getpass import getpass
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from io import BytesIO

from pptx import Presentation


BASE_URL = "http://127.0.0.1:5000"
EXPORT_DIR = Path(__file__).resolve().parent / "exports"


def api_request(url, method="GET", data=None, token=None):
    headers = {}

    if data is not None:
        headers["Content-Type"] = "application/json"

    if token:
        headers["Authorization"] = f"Bearer {token}"

    body = json.dumps(data).encode("utf-8") if data is not None else None
    request = Request(url, data=body, headers=headers, method=method)

    try:
        with urlopen(request, timeout=120) as response:
            return response.status, response.read()

    except HTTPError as error:
        return error.code, error.read()

    except URLError as error:
        raise RuntimeError(
            "Impossible de contacter le serveur Flask. "
            "Vérifiez que python run.py est lancé."
        ) from error


def main():
    print("\n=== TEST EXPORT POWERPOINT ZERO ANOMALIE ===\n")

    username = input("Identifiant : ").strip()
    password = getpass("Mot de passe : ")

    status, response = api_request(
        f"{BASE_URL}/api/auth/login",
        method="POST",
        data={
            "username": username,
            "password": password
        }
    )

    if status != 200:
        print("ÉCHEC CONNEXION :", status)
        print(response.decode("utf-8", errors="replace"))
        return

    login_data = json.loads(response.decode("utf-8"))
    token = login_data["access_token"]
    user = login_data.get("user", {})

    print("\nConnexion réussie.")
    print("Utilisateur :", user.get("full_name"))
    print("Rôle :", user.get("role"))

    if user.get("role") not in ("ADMIN", "CHEF_SECTEUR"):
        print("ERREUR : seuls ADMIN et CHEF_SECTEUR peuvent exporter.")
        return

    print("\nPériode du rapport (format AAAA-MM-JJ)")
    start_date = input("Date de début : ").strip()
    end_date = input("Date de fin : ").strip()

    try:
        datetime.strptime(start_date, "%Y-%m-%d")
        datetime.strptime(end_date, "%Y-%m-%d")
    except ValueError:
        print("Format de date invalide.")
        return

    if end_date < start_date:
        print("La date de fin doit être après la date de début.")
        return

    payload = {
        "start_date": start_date,
        "end_date": end_date
    }

    print("\nGénération du PowerPoint en cours...")

    status, response = api_request(
        f"{BASE_URL}/api/reports/powerpoint",
        method="POST",
        data=payload,
        token=token
    )

    if status != 200:
        print("ÉCHEC EXPORT :", status)
        print(response.decode("utf-8", errors="replace"))
        return

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    filename = (
        f"rapport_zero_anomalie_"
        f"{start_date.replace('-', '')}_"
        f"{end_date.replace('-', '')}.pptx"
    )

    output_path = EXPORT_DIR / filename
    output_path.write_bytes(response)

    try:
        presentation = Presentation(BytesIO(response))
    except Exception as error:
        output_path.unlink(missing_ok=True)
        print("Le fichier reçu n'est pas un PowerPoint valide :", error)
        return

    print("\nEXPORT RÉUSSI !")
    print("Fichier :", output_path)
    print("Taille :", len(response), "octets")
    print("Nombre de diapositives :", len(presentation.slides))


if __name__ == "__main__":
    main()
