#!/usr/bin/env python3
"""
Monitor de citas del Consulado de España en Córdoba.
Navega la web, detecta disponibilidad de turnos y notifica al instante.
"""
import asyncio
import logging
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


async def check_appointments() -> dict:
    """
    Navega la página del consulado, acepta el diálogo, clickea Continuar
    y devuelve el estado de la página.

    Returns:
        dict con keys: status ("available"|"unavailable"|"error"),
                       text (contenido de la página),
                       screenshot (bytes PNG)
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            locale="es-ES",
        )
        page = await context.new_page()

        page.on("dialog", lambda dialog: dialog.accept())

        try:
            logger.info("Navegando a %s", config.CONSULATE_URL)
            await page.goto(config.CONSULATE_URL, wait_until="networkidle", timeout=config.NAVIGATION_TIMEOUT)

            logger.info("Esperando botón 'Continue / Continuar'...")
            continue_btn = page.get_by_role("link", name=config.CONTINUE_BUTTON_TEXT)
            try:
                await continue_btn.wait_for(state="visible", timeout=config.BUTTON_TIMEOUT)
            except PlaywrightTimeout:
                continue_btn = page.get_by_role("button", name=config.CONTINUE_BUTTON_TEXT)
                await continue_btn.wait_for(state="visible", timeout=config.BUTTON_TIMEOUT)

            await continue_btn.click()
            logger.info("Click en 'Continue / Continuar' realizado")

            logger.info("Esperando resultado...")
            await page.wait_for_load_state("networkidle", timeout=config.RESULT_TIMEOUT)
            await page.wait_for_timeout(3000)

            screenshot = await page.screenshot(full_page=True)
            page_text = await page.inner_text("body")
            page_text = page_text.strip()

            logger.info("Texto de la página (primeros 200 chars): %s", page_text[:200])

            if config.NO_APPOINTMENTS_TEXT in page_text:
                logger.info("Estado: SIN turnos disponibles")
                return {"status": "unavailable", "text": page_text, "screenshot": screenshot}

            if "502" in page_text or "Bad Gateway" in page_text:
                logger.warning("Detectado error 502 en la página")
                return {"status": "error", "text": page_text, "screenshot": screenshot}

            logger.info("Estado: CAMBIO DETECTADO — posible disponibilidad!")
            return {"status": "available", "text": page_text, "screenshot": screenshot}

        except PlaywrightTimeout as e:
            logger.error("Timeout durante la navegación: %s", e)
            screenshot = await page.screenshot(full_page=True)
            return {"status": "error", "text": str(e), "screenshot": screenshot}
        except Exception as e:
            logger.error("Error inesperado: %s", e)
            try:
                screenshot = await page.screenshot(full_page=True)
            except Exception:
                screenshot = None
            return {"status": "error", "text": str(e), "screenshot": screenshot}
        finally:
            await browser.close()


async def run_with_retries() -> dict:
    """Ejecuta check_appointments con reintentos para errores transitorios."""
    for attempt in range(1, config.MAX_RETRIES + 1):
        logger.info("--- Intento %d de %d ---", attempt, config.MAX_RETRIES)
        result = await check_appointments()

        if result["status"] != "error":
            return result

        if attempt < config.MAX_RETRIES:
            delay = config.RETRY_DELAYS[attempt - 1]
            logger.info("Reintentando en %d segundos...", delay)
            time.sleep(delay)

    return result


async def main() -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info("=" * 60)
    logger.info("Monitor de citas iniciado: %s", now)
    logger.info("=" * 60)

    result = await run_with_retries()

    if result["status"] == "available":
        logger.info("ALERTA: Posible disponibilidad detectada!")
        notifier.notify_available(result["text"], result["screenshot"])
    elif result["status"] == "error":
        logger.error("El monitor falló después de %d intentos", config.MAX_RETRIES)
        notifier.notify_error(result["text"])
    else:
        logger.info("Sin turnos disponibles. Próximo chequeo en 5 minutos.")

    logger.info("Monitor finalizado.")


if __name__ == "__main__":
    asyncio.run(main())
