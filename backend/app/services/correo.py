"""Entrega de mensajes transaccionales configurados por entorno."""

import logging
import smtplib
import ssl
from email.message import EmailMessage

from flask import current_app


def enviar_enlace_restablecimiento(email, token):
    """Envía el enlace seguro o lo registra en consola solo en modo local explícito."""
    base_url = current_app.config["APP_BASE_URL"]
    enlace = f"{base_url}/restablecer?token={token}"
    host = current_app.config.get("SMTP_HOST")
    if not host:
        if current_app.config.get("PASSWORD_RESET_DEBUG") and current_app.config.get("BIMETRICS_ENV") != "production":
            current_app.logger.warning("Enlace de restablecimiento local para %s: %s", email, enlace)
            return True
        current_app.logger.error("Restablecimiento solicitado sin SMTP configurado.")
        return False

    message = EmailMessage()
    message["Subject"] = "Restablece tu contraseña de BIMetrics"
    message["From"] = current_app.config["SMTP_FROM"]
    message["To"] = email
    message.set_content(
        "Recibimos una solicitud para restablecer la contraseña de tu cuenta BIMetrics.\n\n"
        f"Usa este enlace dentro de los próximos 30 minutos: {enlace}\n\n"
        "Si no solicitaste el cambio, ignora este mensaje. El enlace se puede usar una sola vez."
    )
    try:
        with smtplib.SMTP(host, current_app.config["SMTP_PORT"], timeout=10) as server:
            server.ehlo()
            if current_app.config.get("SMTP_USE_TLS"):
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
            username = current_app.config.get("SMTP_USERNAME")
            if username:
                server.login(username, current_app.config.get("SMTP_PASSWORD", ""))
            server.send_message(message)
    except (OSError, smtplib.SMTPException):
        logging.getLogger(__name__).exception("No se pudo enviar el correo de restablecimiento.")
        return False
    return True
