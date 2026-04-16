import os

# --- URL del Consulado ---
CONSULATE_URL = (
    "https://www.citaconsular.es/es/hosteds/widgetdefault/"
    "298f7f17f58c0836448a99edecf16e66a"
)

# --- Textos conocidos de la página ---
NO_APPOINTMENTS_TEXT = "No hay horas disponibles"
PAGE_TITLE_TEXT = "Consulado General de España en Córdoba"
CONTINUE_BUTTON_TEXT = "Continue"

# --- Timeouts (milisegundos) ---
NAVIGATION_TIMEOUT = 30_000
BUTTON_TIMEOUT = 15_000
RESULT_TIMEOUT = 15_000

# --- Reintentos ---
MAX_RETRIES = 3
RETRY_DELAYS = [5, 15, 30]  # segundos entre reintentos

# --- Notificaciones: ntfy.sh ---
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}" if NTFY_TOPIC else ""

# --- Notificaciones: Email ---
EMAIL_SENDER = os.environ.get("EMAIL_USER", "")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASS", "")
EMAIL_RECIPIENT = os.environ.get("EMAIL_RECIPIENT", EMAIL_SENDER)
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
