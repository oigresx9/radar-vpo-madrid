import os
import requests

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

ICONS = {"CRITICO": "🔴", "IMPORTANTE": "🟠", "INFORMATIVO": "🟢"}


def send_alert(source_name: str, municipio: str, urgencia: str, resumen: str, url: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("[WARN] Faltan TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID. No se envía notificación.")
        return

    icon = ICONS.get(urgencia, "⚪")
    text = (
        f"{icon} *{urgencia}* — Radar VPO Madrid\n\n"
        f"*Fuente:* {source_name}\n"
        f"*Municipio:* {municipio or 'N/D'}\n\n"
        f"{resumen}\n\n"
        f"🔗 {url}"
    )

    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    resp = requests.post(api_url, data={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False,
    }, timeout=15)

    if resp.status_code != 200:
        print(f"[ERROR] Telegram respondió {resp.status_code}: {resp.text}")
