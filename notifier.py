from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from datetime import datetime

import requests

import config

logger = logging.getLogger(__name__)


def send_ntfy(title: str, message: str, priority: str = "urgent", tags: str = "rotating_light") -> bool:
    if not config.NTFY_URL:
        logger.warning("NTFY_TOPIC no configurado, saltando notificación ntfy")
        return False

    try:
        resp = requests.post(
            config.NTFY_URL,
            data=message.encode("utf-8"),
            headers={
                "Title": title,
                "Priority": priority,
                "Tags": tags,
            },
            timeout=10,
        )
        resp.raise_for_status()
        logger.info("Notificación ntfy enviada correctamente")
        return True
    except Exception as e:
        logger.error("Error enviando ntfy: %s", e)
        return False


def send_email(subject: str, body: str, screenshot: bytes | None = None) -> bool:
    if not config.EMAIL_SENDER or not config.EMAIL_PASSWORD:
        logger.warning("Credenciales de email no configuradas, saltando email")
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = config.EMAIL_SENDER
        msg["To"] = config.EMAIL_RECIPIENT
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain", "utf-8"))

        if screenshot:
            img = MIMEImage(screenshot, name="screenshot.png")
            img.add_header("Content-Disposition", "attachment", filename="screenshot.png")
            msg.attach(img)

        with smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT) as server:
            server.starttls()
            server.login(config.EMAIL_SENDER, config.EMAIL_PASSWORD)
            server.sendmail(config.EMAIL_SENDER, config.EMAIL_RECIPIENT, msg.as_string())

        logger.info("Email enviado correctamente a %s", config.EMAIL_RECIPIENT)
        return True
    except Exception as e:
        logger.error("Error enviando email: %s", e)
        return False


def notify_available(page_text: str, screenshot: bytes | None = None) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    title = "CITA CONSULADO DISPONIBLE"
    message = (
        f"[{now}] Se detectó un cambio en la página del consulado.\n\n"
        f"El texto 'No hay horas disponibles' YA NO APARECE.\n\n"
        f"Revisá ahora: {config.CONSULATE_URL}\n\n"
        f"Texto detectado:\n{page_text[:500]}"
    )

    send_ntfy(title, message, priority="urgent", tags="rotating_light,es")
    send_email(f"🚨 {title}", message, screenshot)


def notify_error(error_msg: str) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    title = "Error Monitor Consulado"
    message = f"[{now}] El monitor falló después de todos los reintentos.\n\nError: {error_msg}"

    send_ntfy(title, message, priority="high", tags="warning")
    send_email(title, message)
