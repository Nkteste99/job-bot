from typing import List
import requests

from config.settings import settings
from models.models import Vaga


def send_message(text: str) -> bool:
    """Send a plain HTML-formatted message to the configured chat id using Telegram Bot HTTP API."""
    token = None
    try:
        token = settings.TELEGRAM_BOT_TOKEN.get_secret_value()
    except Exception:
        token = getattr(settings, "TELEGRAM_BOT_TOKEN", None)
    chat_id = settings.TELEGRAM_CHAT_ID
    if not token or not chat_id:
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        data = resp.json()
        return bool(data.get("ok"))
    except Exception:
        return False


def _format_vaga_message(vaga: Vaga) -> str:
    title = vaga.titulo or "—"
    company = vaga.empresa or "—"
    location = vaga.localizacao or "—"
    link = vaga.link or ""
    msg = f"<b>{title}</b>\n{company} — {location}\n{link}"
    return msg


def notify_new_vagas(vagas: List[Vaga]) -> int:
    """Send one message per vaga. Returns number of messages successfully sent."""
    sent = 0
    for vaga in vagas:
        text = _format_vaga_message(vaga)
        if send_message(text):
            sent += 1
    return sent
"""Telegram notifier (minimal placeholder).

Will use `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` from env. For V1 we
send simple text messages via the Bot API using `requests`.
"""
import requests
from config.settings import settings


def send_telegram_message(text: str) -> bool:
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    if not token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(url, json={"chat_id": chat_id, "text": text})
    return resp.status_code == 200
