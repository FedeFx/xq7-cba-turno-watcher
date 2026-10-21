# Monitor de Citas - Consulado de España en Córdoba

Monitor automático que revisa periódicamente (ver [frecuencia real](#cada-cuánto-revisa)) la disponibilidad de turnos para ciudadanía española en el Consulado de España en Córdoba (Argentina). Cuando detecta un cambio, te avisa al celular con una alarma.

## Cómo funciona

1. **GitHub Actions** ejecuta el script periódicamente (cron `*/5`, en la práctica cada ~60-90 min; gratis)
2. **Playwright** abre un navegador, acepta el diálogo, clickea el botón "Continue" (o "Continuar", según el idioma que sirva la web) y lee el resultado de la página y de sus iframes
3. Si el texto "No hay horas disponibles" **desaparece**, te notifica al instante
4. **ntfy.sh** envía una alarma urgente a tu celular (suena incluso en silencio)

## Setup rápido (3 pasos)

### Paso 1: Notificaciones en el celular

1. Instalá la app **ntfy** en tu celular:
   - [Android (Google Play)](https://play.google.com/store/apps/details?id=io.heckel.ntfy)
   - [iOS (App Store)](https://apps.apple.com/app/ntfy/id1625396347)
2. Abrí la app y suscribite a un topic secreto (ej: `consulado-cordoba-mi-nombre-2026`)
   - Usá un nombre largo y único para que nadie más lo use
3. En la config de la suscripción, poné **prioridad mínima = 1** para recibir todo

### Paso 2: Crear el repositorio en GitHub

1. Creá un **nuevo repositorio público** en GitHub (los públicos tienen Actions ilimitadas)
2. Subí todos los archivos de este proyecto
3. Andá a **Settings > Secrets and variables > Actions** y agregá estos secrets:

| Secret | Valor | Requerido |
|--------|-------|-----------|
| `NTFY_TOPIC` | El nombre del topic que elegiste en ntfy (ej: `consulado-cordoba-mi-nombre-2026`) | Sí |
| `EMAIL_USER` | Tu email de Gmail (ej: `tu@gmail.com`) | Opcional |
| `EMAIL_PASS` | App Password de Gmail ([cómo crear una](https://support.google.com/accounts/answer/185833)) | Opcional |
| `EMAIL_RECIPIENT` | Email donde recibir alertas (si es distinto al sender) | Opcional |

### Paso 3: Activar

El workflow se activa solo al hacer push. Para verificar que funciona:

1. Andá a la pestaña **Actions** del repo
2. Seleccioná el workflow "Monitor Citas Consulado"
3. Click en **"Run workflow"** para ejecutarlo manualmente
   - `debug`: loguea el texto completo de la página, URL, título y botones visibles
   - `dry_run`: no envía notificaciones, solo las loguea (para probar sin alertas falsas)
4. Verificá en los logs que dice `ESTADO FINAL: unavailable` / "Sin turnos disponibles" (estado normal)
5. En cada run se sube un artifact `diagnostico-<id>` con `screenshot.png` y `page.html`

### Importante: reactivar el workflow cada 60 días

GitHub **deshabilita automáticamente** los workflows programados de repos públicos tras 60 días sin actividad (commits).
Cuando pasa, el monitor deja de correr sin avisar. Para reactivarlo:

- **Actions > Monitor Citas Consulado > "Enable workflow"**, o
- `gh workflow enable monitor.yml -R <usuario>/<repo>`, o
- hacer cualquier commit en `main` antes de que se cumplan los 60 días.

## Qué detecta

- **Disponibilidad de turnos**: cuando el mensaje "No hay horas disponibles" desaparece
- **Cambios en la página**: cualquier contenido nuevo (calendarios, selectores de fecha, etc.)
- **Página desconocida**: si no aparece "No hay horas disponibles" ni un error claro, se avisa como posible disponibilidad (nunca se toma como error)
- **Bloqueo anti-bots**: si la web muestra la verificación de Cloudflare ("Verificación de seguridad en curso"), el estado es `blocked` y se trata como error (no como disponibilidad). Ver FAQ.
- **Errores del servidor**: 502/503/504 o página vacía, con reintentos automáticos (3 intentos)
- **Anti-spam**: el aviso de error se manda solo tras 3 runs fallidos seguidos (una vez), y llega un aviso cuando se recupera. El run queda en rojo (exit 1) cuando falla.

## Estructura del proyecto

```
├── monitor.py          # Script principal (navegación + detección)
├── notifier.py         # Envío de alertas (ntfy.sh + email)
├── config.py           # Configuración centralizada
├── requirements.txt    # Dependencias Python
├── .github/
│   └── workflows/
│       └── monitor.yml # Cron job de GitHub Actions
└── README.md
```

## Ejecución en tu PC (IP residencial)

Desde GitHub Actions, Cloudflare muestra un desafío anti-bots (estado `blocked`). Desde una conexión
hogareña normalmente no pasa. Para correrlo en tu PC:

```bash
git clone https://github.com/fedefx/xq7-cba-turno-watcher.git
cd xq7-cba-turno-watcher
python -m venv .venv
# Windows: .venv\Scripts\activate      Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
cp .env.example .env                    # Windows: copy .env.example .env  → completá NTFY_TOPIC
```

Prueba (sin notificar, con ventana para ver qué pasa):

```bash
DRY_RUN=1 DEBUG=1 HEADLESS=0 python monitor.py      # Windows (PowerShell): $env:DRY_RUN=1; $env:DEBUG=1; $env:HEADLESS=0; python monitor.py
```

Si termina en `unavailable`, funciona. Para dejarlo corriendo cada 15 minutos:

- **Linux/Mac** (`crontab -e`):
  `*/15 * * * * cd /ruta/al/repo && .venv/bin/python monitor.py >> monitor.log 2>&1`
- **Windows** (Programador de tareas → Crear tarea básica → Diariamente → repetir cada 15 min):
  programa `C:\ruta\al\repo\.venv\Scripts\python.exe`, argumentos `monitor.py`,
  "Iniciar en" `C:\ruta\al\repo`.

## Prueba con Cloudflare WARP en Actions

En Actions → Monitor Citas Consulado → Run workflow, marcá `warp` y `dry_run`. El log del paso
"Connect Cloudflare WARP" muestra la IP antes y después; el resultado del monitor dice si sigue `blocked`.
Si funciona, creá la variable de repo `USE_WARP=true` (Settings → Secrets and variables → Actions →
Variables) para que los runs programados también usen WARP.

## FAQ

**¿Es gratis?**
Sí, 100%. GitHub Actions es gratis para repos públicos y ntfy.sh es gratuito.

**¿Cada cuánto revisa?**
El cron pide cada 5 minutos, pero GitHub Actions no lo garantiza: en la práctica los runs programados salen cada ~60-90 minutos (a veces más en horas pico). Si necesitás más frecuencia, hace falta otro runner (self-hosted, un VPS, etc.).

**¿Qué pasa si el servidor da error 502?**
El script reintenta automáticamente hasta 3 veces con espera progresiva (5s, 15s, 30s).

**¿Me avisa aunque tenga el celular en silencio?**
Sí. Las notificaciones de ntfy con prioridad "urgent" ignoran el modo silencio/no molestar.

**El log dice `ESTADO FINAL: blocked`. ¿Qué pasa?**
citaconsular.es está detrás de Cloudflare Turnstile y, desde las IPs de GitHub Actions, muestra la página "Verificación de seguridad en curso" en vez del widget. Mientras eso pase el monitor no puede ver los turnos. Alternativas: correrlo desde una IP residencial (self-hosted runner en una PC/Raspberry en casa, `runs-on: self-hosted`) o en un navegador no headless con perfil real. Este proyecto no intenta saltear captchas.
