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
