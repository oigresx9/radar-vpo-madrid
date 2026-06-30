# Radar VPO Madrid — MVP

Monitoriza fuentes oficiales de vivienda protegida en la Comunidad de Madrid
y avisa por Telegram cuando detecta un cambio. Corre gratis en GitHub Actions,
sin servidor que mantener.

## Cómo funciona

1. Cada 15 min, GitHub Actions ejecuta `src/main.py`.
2. Por cada fuente en `config/sources.yaml`, descarga la página, limpia el HTML
   (quita nav/footer/scripts) y calcula un hash del texto relevante.
3. Si el hash cambia respecto a la última ejecución -> es una novedad.
4. Clasifica urgencia por palabras clave (🔴 CRITICO / 🟠 IMPORTANTE / 🟢 INFORMATIVO).
5. Manda un mensaje a tu Telegram y lo guarda en `data/radar.db` (historial + dedup).

La primera ejecución NO manda alertas — solo guarda el estado inicial de cada
fuente como punto de partida (si no, te llegarían 6 alertas falsas el primer día).

## Despliegue (15 minutos)

### 1. Crear el bot de Telegram
1. Habla con [@BotFather](https://t.me/BotFather) en Telegram, manda `/newbot`, sigue los pasos.
2. Te dará un **token** tipo `123456789:ABCdefGhIJKlmNoPQRstuVwxyZ`. Guárdalo.
3. Manda cualquier mensaje a tu bot recién creado (para "activar" el chat).
4. Visita `https://api.telegram.org/bot<TU_TOKEN>/getUpdates` en el navegador y busca
   `"chat":{"id": NUMERO ...` — ese NUMERO es tu `TELEGRAM_CHAT_ID`.

### 2. Subir este proyecto a GitHub
```bash
cd radar-vpo-madrid
git init
git add .
git commit -m "Radar VPO Madrid - MVP"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/radar-vpo-madrid.git
git push -u origin main
```

### 3. Configurar los secretos
En GitHub: Settings → Secrets and variables → Actions → New repository secret
- `TELEGRAM_BOT_TOKEN` = el token del paso 1
- `TELEGRAM_CHAT_ID` = el chat id del paso 1

### 4. Lanzarlo
Ve a la pestaña **Actions** del repo → "Radar VPO Madrid" → **Run workflow** (botón manual,
no hace falta esperar 15 min la primera vez). Revisa los logs: debería decir
"Baseline inicial guardada" para cada fuente. A partir de la siguiente ejecución
ya detecta cambios reales.

## Añadir una fuente nueva
Edita `config/sources.yaml` y añade un bloque con `id`, `nombre`, `tipo` (`generic_html`
o `bocm`), `url` y `municipio`. No hace falta tocar código. Commitea y listo.

## Limitaciones conocidas del MVP (a decidir contigo en la siguiente iteración)
- El adapter de BOCM hoy trata el sumario como HTML genérico: cualquier cambio en
  el sumario diario (sea de vivienda o no) dispara alerta. Falta parsear el PDF
  por sección "Vivienda y Urbanismo" para filtrar ruido.
- Los portales de comercialización (Sogeviso, Distrito Vive) no están añadidos
  todavía — dijiste "Avalon, Sogeviso, Distrito Vive cuando sean canal oficial",
  pero no me diste las URLs concretas a vigilar.
- Cron de GitHub Actions no es preciso por debajo de ~5 min reales aunque se pida
  cada minuto; 15 min es razonable y gratis. Si quieres de verdad tiempo real
  (segundos), hace falta un servidor con proceso persistente, no Actions.
- Clasificación de urgencia es por keywords simples, no IA — puede haber falsos
  positivos/negativos al principio; hay que afinar la lista según lo que vayas viendo.
