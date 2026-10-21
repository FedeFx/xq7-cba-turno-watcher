#!/usr/bin/env python3
"""
Monitor de citas del Consulado de España en Córdoba.
Navega la web, detecta disponibilidad de turnos y notifica al instante.
"""
import asyncio
import json
import logging
import re
import sys
import time
from datetime import datetime

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

import config
import notifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

CONTINUE_RE = re.compile(config.CONTINUE_BUTTON_PATTERN, re.IGNORECASE)

# JS que devuelve los textos de links/botones visibles de un frame (solo para debug)
CLICKABLES_JS = """() => Array.from(document.querySelectorAll(
    'a, button, input[type=submit], input[type=button], [role=button]'))
  .filter(e => e.offsetParent !== null)
  .map(e => `${e.tagName.toLowerCase()}: ${(e.innerText || e.value || e.getAttribute('aria-label') || '').trim().slice(0, 80)}`)"""


async def frame_texts(page) -> list:
    """Devuelve [(nombre_frame, innerText)] de la página y de todos sus frames."""
    result = []
    for i, frame in enumerate(page.frames):
        name = "page" if frame == page.main_frame else f"frame[{i}] {frame.url[:100]}"
        try:
            text = await frame.evaluate("() => document.body ? document.body.innerText : ''")
        except Exception as e:
            text = ""
            logger.debug("No se pudo leer %s: %s", name, e)
        result.append((name, (text or "").strip()))
    return result


async def log_debug(page, momento: str) -> None:
    """Loguea URL, título, textos y clickables de cada frame (solo con DEBUG=1)."""
    if not config.DEBUG:
        return
    logger.info("[DEBUG] ===== %s =====", momento)
    logger.info("[DEBUG] URL final: %s", page.url)
    try:
        logger.info("[DEBUG] Título: %s", await page.title())
    except Exception as e:
        logger.info("[DEBUG] Título no disponible: %s", e)
    for i, frame in enumerate(page.frames):
        try:
            clickables = await frame.evaluate(CLICKABLES_JS)
        except Exception as e:
            clickables = [f"(error: {e})"]
        logger.info("[DEBUG] frame[%d] %s -> clickables visibles: %s", i, frame.url[:120], clickables)
    for name, text in await frame_texts(page):
        logger.info("[DEBUG] Texto de %s (%d chars):\n%s", name, len(text), text)


async def find_continue(page):
    """Busca el botón/link 'Continue'/'Continuar' en la página y en sus frames."""
    deadline = time.monotonic() + config.BUTTON_TIMEOUT / 1000
    while time.monotonic() < deadline:
        for frame in page.frames:
            for role in ("link", "button"):
                loc = frame.get_by_role(role, name=CONTINUE_RE).first
                try:
                    if await loc.count() and await loc.is_visible():
                        return loc
                except Exception:
                    pass
        await asyncio.sleep(0.5)
    return None


def classify(texts: list) -> str:
    """
    unavailable si aparece el texto de 'sin horas'; blocked si es la verificación anti-bots;
    error si hay error claro; si no, unknown.
    """
    full = "\n".join(t for _, t in texts)
    if config.NO_APPOINTMENTS_TEXT in full:
        return "unavailable"
    # El nombre del frame incluye su URL (sirve para detectar el iframe de Cloudflare)
    if any(b in name or b in text for name, text in texts for b in config.BLOCKED_TEXTS):
        return "blocked"
    if not full.strip() or any(e in full for e in config.SERVER_ERROR_TEXTS):
        return "error"
    return "unknown"


async def save_diagnostics(page) -> bytes | None:
    """Guarda screenshot.png y page.html (nunca lanza excepción)."""
    screenshot = None
    try:
        screenshot = await page.screenshot(full_page=True)
        with open(config.SCREENSHOT_FILE, "wb") as f:
            f.write(screenshot)
    except Exception as e:
        logger.warning("No se pudo sacar screenshot: %s", e)
    try:
        with open(config.HTML_FILE, "w", encoding="utf-8") as f:
            f.write(await page.content())
    except Exception as e:
        logger.warning("No se pudo guardar el HTML: %s", e)
    return screenshot


async def check_appointments() -> dict:
    """
    Navega la página del consulado, acepta el diálogo, clickea Continue/Continuar
    y devuelve el estado de la página.

    Returns:
        dict con keys: status ("unknown"|"unavailable"|"blocked"|"error"),
                       text (contenido de la página),
                       screenshot (bytes PNG o None)
    """
    async with async_playwright() as p:
        browser = None
        page = None
        try:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                locale="es-ES",
            )
            page = await context.new_page()
            page.on("dialog", lambda dialog: asyncio.ensure_future(dialog.accept()))

            logger.info("Navegando a %s", config.CONSULATE_URL)
            await page.goto(config.CONSULATE_URL, wait_until="load", timeout=config.NAVIGATION_TIMEOUT)
            await log_debug(page, "Antes de clickear Continue")

            logger.info("Buscando botón 'Continue / Continuar'...")
            continue_btn = await find_continue(page)
            if continue_btn is None:
                # No es error: puede que la página ya muestre el resultado directamente
                logger.warning("No se encontró botón 'Continue/Continuar'; se lee la página tal cual")
            else:
                logger.info("Botón encontrado: '%s'", (await continue_btn.inner_text()).strip())
                await continue_btn.click()
                logger.info("Click en 'Continue / Continuar' realizado")

            logger.info("Esperando resultado del widget...")
            # Polling sobre page + frames hasta ver un estado conocido o agotar el timeout
            deadline = time.monotonic() + config.RESULT_TIMEOUT / 1000
            texts = await frame_texts(page)
            status = classify(texts)
            while status != "unavailable" and time.monotonic() < deadline:
                await asyncio.sleep(2)
                texts = await frame_texts(page)
                status = classify(texts)
            await page.wait_for_timeout(1000)
            texts = await frame_texts(page)
            status = classify(texts)

            await log_debug(page, "Resultado")
            screenshot = await save_diagnostics(page)
            page_text = "\n".join(t for _, t in texts).strip()
            where = [n for n, t in texts if config.NO_APPOINTMENTS_TEXT in t]
            logger.info("Texto de la página (primeros 200 chars): %s", page_text[:200])

            if status == "unavailable":
                logger.info("Estado: SIN turnos disponibles (texto encontrado en: %s)", ", ".join(where))
            elif status == "blocked":
                logger.warning("BLOQUEADO: la web muestra la verificación anti-bots de Cloudflare")
            elif status == "error":
                logger.warning("Página vacía o con error del servidor")
            else:
                logger.info("Estado: CAMBIO DETECTADO — página desconocida, posible disponibilidad!")
            return {"status": status, "text": page_text, "screenshot": screenshot}

        except PlaywrightTimeout as e:
            logger.error("Timeout durante la navegación: %s", e)
            screenshot = await save_diagnostics(page) if page else None
            return {"status": "error", "text": str(e), "screenshot": screenshot}
        except Exception as e:
            logger.error("Error inesperado: %s", e)
            screenshot = await save_diagnostics(page) if page else None
            return {"status": "error", "text": str(e), "screenshot": screenshot}
        finally:
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass


async def run_with_retries() -> dict:
    """Ejecuta check_appointments con reintentos para errores transitorios."""
    for attempt in range(1, config.MAX_RETRIES + 1):
        logger.info("--- Intento %d de %d ---", attempt, config.MAX_RETRIES)
        result = await check_appointments()

        if result["status"] not in ("error", "blocked"):
            return result

        if attempt < config.MAX_RETRIES:
            delay = config.RETRY_DELAYS[attempt - 1]
            logger.info("Reintentando en %d segundos...", delay)
            await asyncio.sleep(delay)

    return result


def load_state() -> dict:
    try:
        with open(config.STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"consecutive_errors": 0}


def save_state(state: dict) -> None:
    try:
        with open(config.STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f)
    except Exception as e:
        logger.warning("No se pudo guardar el estado: %s", e)


async def main() -> int:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info("=" * 60)
    logger.info("Monitor de citas iniciado: %s%s%s", now,
                " [DEBUG]" if config.DEBUG else "", " [DRY_RUN]" if config.DRY_RUN else "")
    logger.info("=" * 60)

    state = load_state()
    prev_errors = int(state.get("consecutive_errors", 0))
    result = await run_with_retries()
    status = result["status"]
    logger.info("ESTADO FINAL: %s", status)

    if status in ("error", "blocked"):
        errors = prev_errors + 1
        logger.error("El monitor falló después de %d intentos (%d runs fallidos seguidos)",
                     config.MAX_RETRIES, errors)
        if errors == config.ERROR_ALERT_THRESHOLD:
            msg = result["text"]
            if status == "blocked":
                msg = "La web bloquea al monitor con una verificación anti-bots (Cloudflare).\n\n" + msg
            notifier.notify_error(msg, errors)
        else:
            logger.info("Aviso de error omitido (umbral: %d runs seguidos)", config.ERROR_ALERT_THRESHOLD)
        save_state({"consecutive_errors": errors})
        logger.info("Monitor finalizado con error.")
        return 1

    if prev_errors >= config.ERROR_ALERT_THRESHOLD:
        notifier.notify_recovered(prev_errors)
    save_state({"consecutive_errors": 0})

    if status in ("available", "unknown"):
        logger.info("ALERTA: Posible disponibilidad detectada!")
        notifier.notify_available(result["text"], result["screenshot"], unknown=(status == "unknown"))
    else:
        logger.info("Sin turnos disponibles.")

    logger.info("Monitor finalizado.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
