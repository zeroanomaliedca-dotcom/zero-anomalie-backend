
from datetime import timezone
from email.message import EmailMessage
from email.utils import formatdate, parseaddr
from pathlib import Path
from zoneinfo import ZoneInfo
import mimetypes
import re
import smtplib
import ssl

from flask import current_app
from app.extensions import db
from app.models import Category, Sector, User


_EMAIL_RE = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9]"
    r"(?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$"
)
MAX_RECIPIENTS = 20


def _format_datetime(value):
    if value is None:
        return "Non renseignée"
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(
        ZoneInfo("Africa/Casablanca")
    ).strftime("%d/%m/%Y à %H:%M:%S")


def _validated_recipients(recipients):
    if not isinstance(recipients, list) or not recipients:
        raise ValueError("Veuillez saisir au moins une adresse e-mail.")

    if len(recipients) > MAX_RECIPIENTS:
        raise ValueError(f"Maximum {MAX_RECIPIENTS} destinataires autorisés.")

    cleaned = []
    for item in recipients:
        if not isinstance(item, str):
            raise ValueError("Une adresse e-mail est invalide.")
        address = item.strip()
        parsed = parseaddr(address)[1]
        if not parsed or parsed != address or not _EMAIL_RE.fullmatch(address):
            raise ValueError(f"Adresse e-mail invalide : {address or 'vide'}.")
        if address.lower() not in {value.lower() for value in cleaned}:
            cleaned.append(address)

    return cleaned


def _safe_attachment_path(upload_folder, relative_path):
    root = Path(upload_folder).resolve()
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        current_app.logger.warning(
            "Pièce jointe ignorée : chemin hors du dossier uploads (%s)",
            relative_path,
        )
        return None
    return candidate if candidate.is_file() else None


def send_manual_anomaly_email(anomaly, recipients):
    """Envoie manuellement les détails d'une anomalie."""
    try:
        to_recipients = _validated_recipients(recipients)

        mail_username = current_app.config.get("MAIL_USERNAME")
        mail_password = current_app.config.get("MAIL_PASSWORD")
        sender = current_app.config.get("MAIL_DEFAULT_SENDER") or mail_username

        if not mail_username or not mail_password or not sender:
            return False, "Configuration e-mail incomplète sur le serveur."

        sector = db.session.get(Sector, anomaly.sector_id)
        category = db.session.get(Category, anomaly.category_id)
        technician = db.session.get(User, anomaly.technician_id)

        sector_name = sector.name if sector else "Non renseigné"
        category_name = category.name if category else "Non renseignée"
        technician_name = technician.full_name if technician else "Non renseigné"

        latitude = str(anomaly.latitude) if anomaly.latitude is not None else "Non renseignée"
        longitude = str(anomaly.longitude) if anomaly.longitude is not None else "Non renseignée"

        maps_url = None
        if anomaly.latitude is not None and anomaly.longitude is not None:
            maps_url = (
                f"https://www.google.com/maps?q={anomaly.latitude},{anomaly.longitude}"
            )

        message = EmailMessage()
        message["Subject"] = (
            f"[ZÉRO ANOMALIE] {anomaly.reference} - {sector_name}"
        )
        message["From"] = sender
        message["To"] = ", ".join(to_recipients)
        message["Date"] = formatdate(localtime=True)

        body = f"""Bonjour,

Veuillez trouver ci-dessous les informations de l'anomalie réseau.

RÉFÉRENCE : {anomaly.reference}
Titre : {anomaly.title}
Catégorie : {category_name}
Secteur : {sector_name}
Technicien déclarant : {technician_name}
Date de déclaration : {_format_datetime(anomaly.created_at)}
Statut : {anomaly.status}

LOCALISATION
Adresse : {anomaly.location_address or "Non renseignée"}
Latitude : {latitude}
Longitude : {longitude}
Google Maps : {maps_url or "Coordonnées non renseignées"}

DESCRIPTION
{anomaly.description or "Aucune description"}

Les photos initiales disponibles sont jointes à ce message.

Cordialement,
Application ZÉRO ANOMALIE
"""
        message.set_content(body)

        upload_folder = current_app.config["UPLOAD_FOLDER"]
        attached_count = 0

        for photo in anomaly.photos:
            if photo.photo_type != "AVANT":
                continue

            path = _safe_attachment_path(upload_folder, photo.file_path)
            if not path:
                current_app.logger.warning(
                    "Photo initiale introuvable ou ignorée pour %s : %s",
                    anomaly.reference,
                    photo.file_path,
                )
                continue

            content_type, _ = mimetypes.guess_type(path.name)
            if not content_type:
                content_type = "application/octet-stream"

            maintype, subtype = content_type.split("/", 1)

            with path.open("rb") as file_handle:
                message.add_attachment(
                    file_handle.read(),
                    maintype=maintype,
                    subtype=subtype,
                    filename=path.name,
                )

            attached_count += 1

        mail_server = current_app.config.get("MAIL_SERVER", "smtp.gmail.com")
        mail_port = int(current_app.config.get("MAIL_PORT", 587))
        use_tls = current_app.config.get("MAIL_USE_TLS", True)

        with smtplib.SMTP(mail_server, mail_port, timeout=30) as smtp:
            if use_tls:
                smtp.starttls(context=ssl.create_default_context())
            smtp.login(mail_username, mail_password)
            smtp.send_message(
                message,
                from_addr=sender,
                to_addrs=to_recipients,
            )

        current_app.logger.info(
            "E-mail manuel envoyé pour %s à %s (%s photo(s)).",
            anomaly.reference,
            ", ".join(to_recipients),
            attached_count,
        )

        return True, f"E-mail envoyé à {len(to_recipients)} destinataire(s)."

    except ValueError as error:
        return False, str(error)

    except Exception:
        current_app.logger.exception(
            "Échec de l'envoi manuel pour l'anomalie %s.",
            getattr(anomaly, "reference", "inconnue"),
        )
        return (
            False,
            "Échec de l'envoi. Vérifiez la configuration e-mail et les journaux du serveur.",
        )
