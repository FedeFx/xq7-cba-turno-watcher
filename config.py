import os

# --- URL del Consulado ---
CONSULATE_URL = (
    "https://www.citaconsular.es/es/hosteds/widgetdefault/"
    "298f7f17f58c0836448a99edecf16e66a"
)

# --- Textos conocidos de la página ---
NO_APPOINTMENTS_TEXT = "No hay horas disponibles"
# El botón puede decir "Continue" o "Continuar": se busca por regex /continu/i
CONTINUE_BUTTON_PATTERN = r"continu"
# Textos que indican un error claro del servidor (no una página desconocida)
SERVER_ERROR_TEXTS = [
    "502 Bad Gateway",
    "Bad Gateway",
    "503 Service",
    "Service Unavailable",
    "504 Gateway",
    "Gateway Time-out",
]

# --- Timeouts (milisegundos) ---
NAVIGATION_TIMEOUT = 45_000
BUTTON_TIMEOUT = 20_000
# Tras "Continue" el widget puede tardar; no usar networkidle (muchas páginas nunca quedan "idle")
RESULT_TIMEOUT = 60_000

# --- Reintentos ---
MAX_RETRIES = 3
RETRY_DELAYS = [5, 15, 30]  # segundos entre reintentos

# --- Anti-spam de errores ---
# Solo se avisa por error tras N runs fallidos seguidos (y una sola vez hasta recuperarse)
ERROR_ALERT_THRESHOLD = int(os.environ.get("ERROR_ALERT_THRESHOLD", "3"))
STATE_FILE = os.environ.get("STATE_FILE", "state.json")

# --- Archivos de diagnóstico (se suben como artifact en Actions) ---
SCREENSHOT_FILE = "screenshot.png"
HTML_FILE = "page.html"

# --- Modos ---
DEBUG = os.environ.get("DEBUG", "") not in ("", "0", "false")
DRY_RUN = os.environ.get("DRY_RUN", "") not in ("", "0", "false")

# --- Notificaciones: ntfy.sh ---
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "")
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}" if NTFY_TOPIC else ""

# --- Notificaciones: Email ---
EMAIL_SENDER = os.environ.get("EMAIL_USER", "")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASS", "")
EMAIL_RECIPIENT = os.environ.get("EMAIL_RECIPIENT", EMAIL_SENDER)
SMTP_SERVER = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
