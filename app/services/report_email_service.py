
import smtplib
import ssl

from email.message import EmailMessage
from email.utils import formatdate

from flask import current_app


REPORT_RECIPIENT = "i.elayyate@iam.ma"

POWERPOINT_MIMETYPE = (
    "application/vnd.openxmlformats-officedocument.presentationml.presentation"
)


def send_powerpoint_report(
    powerpoint_file,
    filename,
    start_date,
    end_date,
    sector_names,
    category_names=None,
):
    """
    Envoie le rapport PowerPoint par e-mail.

    Ce service est indépendant des notifications de traitement.
    """

    try:
        mail_username = current_app.config.get("MAIL_USERNAME")
        mail_password = current_app.config.get("MAIL_PASSWORD")

        sender = (
            current_app.config.get("MAIL_DEFAULT_SENDER")
            or mail_username
        )

        if not mail_username or not mail_password or not sender:
            current_app.logger.error(
                "Configuration Gmail incomplète pour le rapport."
            )
            return False, "Configuration Gmail incomplète."

        if hasattr(powerpoint_file, "seek"):
            powerpoint_file.seek(0)

        if hasattr(powerpoint_file, "read"):
            attachment_data = powerpoint_file.read()
        else:
            attachment_data = powerpoint_file

        if not isinstance(attachment_data, bytes) or not attachment_data:
            return False, "Le fichier PowerPoint est vide ou invalide."

        sectors_text = ", ".join(sector_names) or "Aucun secteur"
        categories_text = (
            ", ".join(category_names)
            if category_names is not None
            else "Toutes les catégories"
        )

        message = EmailMessage()

        message["Subject"] = (
            f"[ZÉRO ANOMALIE] Rapport PowerPoint "
            f"du {start_date.strftime('%d/%m/%Y')} "
            f"au {end_date.strftime('%d/%m/%Y')}"
        )

        message["From"] = sender
        message["To"] = REPORT_RECIPIENT
        message["Date"] = formatdate(localtime=True)

        text_body = f"""
Bonjour,

Veuillez trouver en pièce jointe le rapport PowerPoint
généré depuis l'application ZÉRO ANOMALIE.

Période : du {start_date.strftime('%d/%m/%Y')}
au {end_date.strftime('%d/%m/%Y')}

Secteurs : {sectors_text}

Catégories : {categories_text}

Cordialement,
Équipe ZÉRO ANOMALIE
"""

        message.set_content(text_body)

        message.add_attachment(
            attachment_data,
            maintype="application",
            subtype=(
                "vnd.openxmlformats-officedocument.presentationml.presentation"
            ),
            filename=filename,
        )

        mail_server = current_app.config.get(
            "MAIL_SERVER",
            "smtp.gmail.com",
        )

        mail_port = int(
            current_app.config.get("MAIL_PORT", 587)
        )

        use_tls = current_app.config.get("MAIL_USE_TLS", True)

        with smtplib.SMTP(
            mail_server,
            mail_port,
            timeout=30,
        ) as smtp:

            if use_tls:
                smtp.starttls(
                    context=ssl.create_default_context()
                )

            smtp.login(mail_username, mail_password)

            smtp.send_message(
                message,
                from_addr=sender,
                to_addrs=[REPORT_RECIPIENT],
            )

        current_app.logger.info(
            "Rapport PowerPoint envoyé à %s : %s",
            REPORT_RECIPIENT,
            filename,
        )

        return True, "Rapport PowerPoint envoyé avec succès."

    except Exception:
        current_app.logger.exception(
            "Erreur lors de l'envoi du rapport PowerPoint."
        )

        return False, (
            "Échec de l'envoi du rapport. "
            "Vérifiez la configuration Gmail et les journaux du serveur."
        )
