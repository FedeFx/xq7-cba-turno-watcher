# Monitor de Citas - Consulado de España en Córdoba

Monitor automático que revisa cada 5 minutos la disponibilidad de turnos para ciudadanía española en el Consulado de España en Córdoba (Argentina). Cuando detecta un cambio, te avisa al celular con una alarma.

## Cómo funciona

1. **GitHub Actions** ejecuta el script cada 5 minutos (gratis)
2. **Playwright** abre un navegador, acepta el diálogo, clickea "Continuar" y lee el resultado
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
4. Verificá en los logs que dice "Sin turnos disponibles" (estado normal)

## Qué detecta

- **Disponibilidad de turnos**: cuando el mensaje "No hay horas disponibles" desaparece
- **Cambios en la página**: cualquier contenido nuevo (calendarios, selectores de fecha, etc.)
- **Errores del servidor**: error 502 con reintentos automáticos (3 intentos)

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

## Ejecución local (opcional)

```bash
pip install -r requirements.txt
playwright install chromium
NTFY_TOPIC=tu-topic python monitor.py
```

## FAQ

**¿Es gratis?**
Sí, 100%. GitHub Actions es gratis para repos públicos y ntfy.sh es gratuito.

**¿Cada cuánto revisa?**
Cada 5 minutos. GitHub Actions no garantiza exactitud al segundo, pero la variación es mínima.

**¿Qué pasa si el servidor da error 502?**
El script reintenta automáticamente hasta 3 veces con espera progresiva (5s, 15s, 30s).

**¿Me avisa aunque tenga el celular en silencio?**
Sí. Las notificaciones de ntfy con prioridad "urgent" ignoran el modo silencio/no molestar.
