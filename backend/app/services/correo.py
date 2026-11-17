"""Entrega de mensajes transaccionales configurados por entorno."""

import logging
import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import urlsplit

from flask import current_app


def modo_restablecimiento_local():
    config = current_app.config
    return config.get("PASSWORD_RESET_DEBUG") and config.get("BIMETRICS_ENV") != "production" and not config.get("SMTP_HOST")


def correo_restablecimiento_disponible():
    config = current_app.config
    if modo_restablecimiento_local():
        return True
    url = urlsplit(config["APP_BASE_URL"])
    esquema = {"https"} if config.get("BIMETRICS_ENV") == "production" else {"http", "https"}
    return bool(config.get("SMTP_HOST") and config.get("SMTP_FROM") and url.hostname and url.scheme in esquema)


def enviar_enlace_restablecimiento(email, token):
    """Envía un enlace con el transporte SMTP configurado."""
    base_url = current_app.config["APP_BASE_URL"]
    enlace = f"{base_url}/restablecer?token={token}"
    host = current_app.config.get("SMTP_HOST")
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
        puerto = current_app.config["SMTP_PORT"]
        tls_directo = current_app.config.get("SMTP_USE_SSL")
        servidor = (
            smtplib.SMTP_SSL(host, puerto, timeout=10, context=ssl.create_default_context())
            if tls_directo else smtplib.SMTP(host, puerto, timeout=10)
        )
        with servidor as server:
            server.ehlo()
            if not tls_directo and current_app.config.get("SMTP_USE_TLS"):
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
