from datetime import timezone
from email.message import EmailMessage
from email.utils import formatdate
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo
import mimetypes
import smtplib
import ssl
import unicodedata

from flask import current_app

from app.extensions import db
from app.models import Category, Sector, User


# Destinataires configurés selon le secteur de l'anomalie.
SECTOR_RECIPIENTS = {
    "INZEGANE": {
        "to": ["i.elayyate@iam.ma"],
        "cc": [],
    },
    "AIT MELLOUL": {
        "to": ["i.elayyate@iam.ma"],
        "cc": [],
    },
    "AGADIR": {
        "to": ["i.elayyate@iam.ma"],
        "cc": [],
    },
}


def _normalize_sector_name(value):
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(
        char for char in value
        if not unicodedata.combining(char)
    )
    return " ".join(value.upper().replace("_", " ").split())


def _format_datetime(value):
    if value is None:
        return "Non renseignée"

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return value.astimezone(
        ZoneInfo("Africa/Casablanca")
    ).strftime("%d/%m/%Y à %H:%M:%S")


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


def _html_table(rows):
    """Construit un tableau HTML sécurisé à partir de libellés et valeurs."""
    table_rows = []

    for label, value in rows:
        table_rows.append(
            f"""
            <tr>
                <td style="padding:10px 12px;background:#F2F5F9;
                           border:1px solid #DCE3EC;width:34%;
                           font-weight:bold;color:#526176;vertical-align:top;">
                    {escape(str(label))}
                </td>
                <td style="padding:10px 12px;border:1px solid #DCE3EC;
                           color:#172B45;vertical-align:top;">
                    {escape(str(value if value not in (None, "") else "Non renseigné"))}
                </td>
            </tr>
            """
        )

    return (
        '<table role="presentation" width="100%" cellspacing="0" '
        'cellpadding="0" style="border-collapse:collapse;'
        'font-family:Arial,sans-serif;font-size:13px;">'
        + "".join(table_rows)
        + "</table>"
    )


def _build_declaration_html(data, technician_name, maps_url=None):
    maps_link = ""

    if maps_url:
        maps_link = (
            '<p style="margin-top:18px;">'
            f'<a href="{escape(maps_url, quote=True)}" '
            'style="color:#1769AA;font-weight:bold;">'
            'Ouvrir la localisation dans Google Maps</a></p>'
        )

    return f"""
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width">
    </head>
    <body style="margin:0;padding:20px 10px;background:#F1F4F8;
                 font-family:Arial,Helvetica,sans-serif;color:#172B45;">
        <div style="max-width:760px;margin:0 auto;background:#FFFFFF;
                    border:1px solid #E1E7EF;border-radius:8px;overflow:hidden;">
            <div style="padding:22px 25px;background:#142B49;color:#FFFFFF;">
                <div style="font-size:22px;font-weight:bold;">ZÉRO ANOMALIE</div>
                <div style="margin-top:5px;font-size:12px;color:#D6E1EF;">
                    GESTION ET SUIVI DES ANOMALIES RÉSEAU
                </div>
            </div>
            <div style="padding:25px;">
                <h2 style="margin-top:0;color:#142B49;">
                    Nouvelle déclaration d'une anomalie
                </h2>
                <p>Bonjour,</p>
                <p>Une nouvelle anomalie réseau vient d'être déclarée
                   via l'application <strong>ZÉRO ANOMALIE</strong>.</p>
                <div style="display:inline-block;padding:9px 13px;
                            background:#FFF4DF;color:#A15C00;
                            border-radius:5px;font-weight:bold;font-size:12px;">
                    EN ATTENTE
                </div>
                <div style="margin:18px 0;padding:14px 16px;
                            background:#F4F6F9;border-left:4px solid #D69B32;">
                    <div style="font-size:11px;color:#526176;">
                        RÉFÉRENCE DE L'ANOMALIE
                    </div>
                    <div style="margin-top:5px;font-size:19px;
                                font-weight:bold;color:#142B49;">
                        {escape(str(data["reference"]))}
                    </div>
                </div>
                <h3 style="color:#142B49;">1. Informations générales</h3>
                {_html_table(data["general"])}
                <h3 style="margin-top:25px;color:#142B49;">2. Localisation</h3>
                {_html_table(data["location"])}
                {maps_link}
                <h3 style="margin-top:25px;color:#142B49;">3. Technicien déclarant</h3>
                <p>{escape(str(technician_name))}</p>
                <div style="margin-top:22px;padding:15px;background:#EFF5FC;
                            border:1px solid #DCE7F4;">
                    Les photos initiales prises lors de la déclaration
                    sont jointes à ce message.
                </div>
                <p style="margin-top:24px;color:#526176;">
                    Nous vous remercions de prendre connaissance de cette
                    déclaration et d'assurer le suivi nécessaire.
                </p>
                <div style="border-top:1px solid #E5EAF0;margin-top:25px;
                            padding-top:18px;color:#526176;font-size:12px;">
                    Cordialement,<br>
                    <strong style="color:#142B49;">Équipe ZÉRO ANOMALIE</strong><br>
                    Application de gestion et de suivi des anomalies réseau
                </div>
            </div>
        </div>
    </body>
    </html>
    """


def _send_message(message, to_recipients, cc_recipients, sender,
                  mail_username, mail_password):
    all_recipients = list(dict.fromkeys(to_recipients + cc_recipients))
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
            to_addrs=all_recipients,
        )


def _get_mail_configuration(sector_name):
    recipients = SECTOR_RECIPIENTS.get(
        _normalize_sector_name(sector_name)
    )

    if not recipients:
        return None, None, None, None, (
            False,
            f"Aucun destinataire configuré pour le secteur {sector_name}.",
        )

    to_recipients = [
        email.strip()
        for email in recipients.get("to", [])
        if email and email.strip()
    ]
    cc_recipients = [
        email.strip()
        for email in recipients.get("cc", [])
        if email and email.strip()
    ]

    if not to_recipients:
        return None, None, None, None, (
            False,
            "Aucun destinataire principal configuré.",
        )

    mail_username = current_app.config.get("MAIL_USERNAME")
    mail_password = current_app.config.get("MAIL_PASSWORD")
    sender = (
        current_app.config.get("MAIL_DEFAULT_SENDER")
        or mail_username
    )

    if not mail_username or not mail_password or not sender:
        return None, None, None, None, (
            False,
            "Configuration Gmail incomplète.",
        )

    return (
        to_recipients,
        cc_recipients,
        sender,
        (mail_username, mail_password),
        None,
    )


def send_treatment_notification(anomaly, handler, action_at):
    """Envoie l'e-mail de prise en charge. Retourne (succès, motif)."""
    try:
        sector = db.session.get(Sector, anomaly.sector_id)
        category = db.session.get(Category, anomaly.category_id)
        technician = db.session.get(User, anomaly.technician_id)

        sector_name = sector.name if sector else "Secteur inconnu"
        (
            to_recipients,
            cc_recipients,
            sender,
            credentials,
            error,
        ) = _get_mail_configuration(sector_name)

        if error:
            current_app.logger.error(error[1])
            return error

        mail_username, mail_password = credentials
        latitude = (
            str(anomaly.latitude)
            if anomaly.latitude is not None
            else "Non renseignée"
        )
        longitude = (
            str(anomaly.longitude)
            if anomaly.longitude is not None
            else "Non renseignée"
        )
        technician_name = (
            technician.full_name if technician else "Non renseigné"
        )
        handler_name = (
            getattr(handler, "full_name", None)
            or getattr(handler, "username", "Responsable inconnu")
        )
        category_name = category.name if category else "Non renseignée"
        location_address = anomaly.location_address or "Non renseignée"
        declaration_method = (
            anomaly.declaration_method or "Non renseignée"
        )

        message = EmailMessage()
        message["Subject"] = (
            f"[ZÉRO ANOMALIE] Prise en charge - "
            f"{anomaly.reference} - {sector_name}"
        )
        message["From"] = sender
        message["To"] = ", ".join(to_recipients)
        if cc_recipients:
            message["Cc"] = ", ".join(cc_recipients)
        message["Date"] = formatdate(localtime=True)

        body = f"""Bonjour,

Une anomalie réseau vient d'être prise en charge dans l'application ZÉRO ANOMALIE.

DÉTAILS DE L'ANOMALIE
Référence : {anomaly.reference}
Titre : {anomaly.title}
Description : {anomaly.description}
Secteur : {sector_name}
Catégorie : {category_name}
Méthode de déclaration : {declaration_method}
Statut : EN_COURS_DE_TRAITEMENT
Date de déclaration : {_format_datetime(anomaly.created_at)}

LOCALISATION
Adresse / emplacement : {location_address}
Latitude : {latitude}
Longitude : {longitude}

INTERVENANTS
Technicien déclarant : {technician_name}
Pris en charge par : {handler_name}
Rôle : {getattr(handler, 'role', 'Non renseigné')}
Date et heure de prise en charge : {_format_datetime(action_at)}

Les photos initiales de déclaration sont jointes à ce message.

Cordialement,
Application ZÉRO ANOMALIE
"""
        message.set_content(body)

        upload_folder = current_app.config["UPLOAD_FOLDER"]
        attached_count = 0

        for photo in anomaly.photos:
            if photo.photo_type != "AVANT":
                continue

            path = _safe_attachment_path(
                upload_folder,
                photo.file_path,
            )
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

        if attached_count == 0:
            current_app.logger.warning(
                "Aucune photo AVANT jointe à l'e-mail de l'anomalie %s.",
                anomaly.reference,
            )

        _send_message(
            message,
            to_recipients,
            cc_recipients,
            sender,
            mail_username,
            mail_password,
        )

        current_app.logger.info(
            "E-mail de prise en charge envoyé pour l'anomalie %s.",
            anomaly.reference,
        )
        return True, "E-mail envoyé."

    except Exception:
        current_app.logger.exception(
            "Échec de l'envoi de l'e-mail pour l'anomalie %s.",
            getattr(anomaly, "reference", "inconnue"),
        )
        return (
            False,
            "Échec de l'envoi de l'e-mail. Vérifiez la configuration Gmail "
            "et les journaux du serveur.",
        )


def send_declaration_notification(anomaly):
    """Envoie un e-mail HTML lors de la déclaration d'une anomalie."""
    try:
        sector = db.session.get(Sector, anomaly.sector_id)
        category = db.session.get(Category, anomaly.category_id)
        technician = db.session.get(User, anomaly.technician_id)

        sector_name = sector.name if sector else "Secteur inconnu"
        category_name = category.name if category else "Non renseignée"

        (
            to_recipients,
            cc_recipients,
            sender,
            credentials,
            error,
        ) = _get_mail_configuration(sector_name)

        if error:
            current_app.logger.error(error[1])
            return error

        mail_username, mail_password = credentials
        technician_name = (
            technician.full_name if technician else "Non renseigné"
        )

        latitude = anomaly.latitude
        longitude = anomaly.longitude
        maps_url = None

        if latitude is not None and longitude is not None:
            maps_url = (
                f"https://www.google.com/maps?q={latitude},{longitude}"
            )

        location_rows = [
            (
                "Adresse",
                anomaly.location_address or "Non renseignée",
            ),
            (
                "Latitude",
                latitude if latitude is not None else "Non renseignée",
            ),
            (
                "Longitude",
                longitude if longitude is not None else "Non renseignée",
            ),
        ]

        data = {
            "reference": anomaly.reference,
            "general": [
                ("Référence", anomaly.reference),
                ("Titre", anomaly.title),
                ("Description", anomaly.description),
                ("Secteur", sector_name),
                ("Catégorie", category_name),
                (
                    "Méthode de déclaration",
                    anomaly.declaration_method or "Non renseignée",
                ),
                ("Statut", "EN ATTENTE"),
                (
                    "Date de déclaration",
                    _format_datetime(anomaly.created_at),
                ),
            ],
            "location": location_rows,
        }

        message = EmailMessage()
        message["Subject"] = (
            f"[ZÉRO ANOMALIE] Nouvelle déclaration - "
            f"{anomaly.reference} - {sector_name}"
        )
        message["From"] = sender
        message["To"] = ", ".join(to_recipients)
        if cc_recipients:
            message["Cc"] = ", ".join(cc_recipients)
        message["Date"] = formatdate(localtime=True)

        text_body = f"""Bonjour,

Une nouvelle anomalie réseau vient d'être déclarée dans ZÉRO ANOMALIE.

Référence : {anomaly.reference}
Titre : {anomaly.title}
Description : {anomaly.description}
Secteur : {sector_name}
Catégorie : {category_name}
Statut : EN ATTENTE
Technicien déclarant : {technician_name}
Date : {_format_datetime(anomaly.created_at)}

Adresse : {anomaly.location_address or "Non renseignée"}
Latitude : {latitude if latitude is not None else "Non renseignée"}
Longitude : {longitude if longitude is not None else "Non renseignée"}
{("Google Maps : " + maps_url) if maps_url else ""}

Les photos initiales sont jointes à ce message.

Cordialement,
Équipe ZÉRO ANOMALIE
"""
        message.set_content(text_body)
        message.add_alternative(
            _build_declaration_html(
                data,
                technician_name,
                maps_url,
            ),
            subtype="html",
        )

        upload_folder = current_app.config["UPLOAD_FOLDER"]
        attached_count = 0

        for photo in anomaly.photos:
            if photo.photo_type != "AVANT":
                continue

            path = _safe_attachment_path(
                upload_folder,
                photo.file_path,
            )
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

        if attached_count == 0:
            current_app.logger.warning(
                "Aucune photo AVANT jointe à l'e-mail de déclaration %s.",
                anomaly.reference,
            )

        _send_message(
            message,
            to_recipients,
            cc_recipients,
            sender,
            mail_username,
            mail_password,
        )

        current_app.logger.info(
            "E-mail de déclaration envoyé pour %s (%s photo(s)).",
            anomaly.reference,
            attached_count,
        )
        return True, "E-mail de déclaration envoyé."

    except Exception:
        current_app.logger.exception(
            "Échec de l'e-mail de déclaration pour %s.",
            getattr(anomaly, "reference", "inconnue"),
        )
        return (
            False,
            "Échec de l'envoi de l'e-mail de déclaration. "
            "Vérifiez la configuration Gmail et les journaux du serveur.",
        )
