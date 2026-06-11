from typing import List, Optional
import logging
import requests

from config.settings import settings
from models.models import Vaga


def send_message(text: str, vaga_id: Optional[str] = None) -> bool:
    """Send a plain HTML-formatted message to the configured chat id using Telegram Bot HTTP API.

    If `vaga_id` is provided and the API returns a non-OK response, an error line
    will be logged to the project log so it can be traced: "TELEGRAM ERROR: {vaga_id} — {status_code}".
    """
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
        status = resp.status_code
        try:
            data = resp.json()
        except Exception:
            data = {}
        ok = bool(data.get("ok")) or (status == 200)
        if not ok and vaga_id:
            logging.error(f"TELEGRAM ERROR: {vaga_id} — {status}")
        return ok
    except Exception:
        if vaga_id:
            logging.error(f"TELEGRAM ERROR: {vaga_id} — exception")
        return False


def _format_vaga_message(vaga: Vaga) -> str:
    """Build the HTML message for a `Vaga` according to the requested layout.

    Only include lines for fields that are present and non-empty.
    """
    lines = []

    # Company
    company = (getattr(vaga, "empresa", None) or "").strip()
    if company:
        lines.append(f"🏢 {company}")

    # Title
    title = (getattr(vaga, "titulo", None) or "").strip()
    if title:
        lines.append(f"💼 {title}")

    # Location: expect `localizacao` as "city - state" already
    location = (getattr(vaga, "localizacao", None) or "").strip()
    if location:
        lines.append(f"📍 {location}")

    # Modalidade: combine isRemoteWork and workplaceType when available
    modality = None
    # try explicit attributes that may exist on the Vaga (collector may add them)
    is_remote = None
    workplace = None
    for key in ("isRemoteWork", "is_remote", "isremotework"):
        if hasattr(vaga, key):
            is_remote = getattr(vaga, key)
            break
        is_remote = getattr(vaga, "__dict__", {}).get(key) if isinstance(getattr(vaga, "__dict__", {}), dict) else None
        if is_remote is not None:
            break
    for key in ("workplaceType", "workplace_type", "workplace", "modalidade", "modality"):
        if hasattr(vaga, key):
            workplace = getattr(vaga, key)
            break
        workplace = getattr(vaga, "__dict__", {}).get(key) if isinstance(getattr(vaga, "__dict__", {}), dict) else None
        if workplace:
            break

    if is_remote and not workplace:
        modality = "Remoto"
    elif workplace:
        w = str(workplace).lower()
        if "on-site" in w or "on_site" in w or "on site" in w or "on-site" in w:
            modality = "Presencial"
        elif "remote" in w:
            modality = "Remoto"
        elif "hybrid" in w:
            modality = "Híbrido"
        elif w in ("on-site", "on_site", "onsite"):
            modality = "Presencial"
        else:
            modality = str(workplace)
    if modality:
        lines.append(f"🏠 {modality}")

    # Application deadline: try several possible attribute names
    deadline = None
    for key in ("applicationDeadline", "application_deadline", "applicationDeadlineFormatted", "prazo", "applicationDeadline_date"):
        val = getattr(vaga, key, None) if hasattr(vaga, key) else None
        if val is None:
            val = getattr(vaga, "__dict__", {}).get(key)
        if val:
            deadline = val
            break
    # format ISO date to DD/MM/YYYY when possible
    if isinstance(deadline, str) and len(deadline) >= 10:
        try:
            # accept ISO-like strings
            from datetime import datetime as _dt

            parsed = _dt.fromisoformat(deadline.replace("Z", "+00:00"))
            deadline = parsed.strftime("%d/%m/%Y")
        except Exception:
            # fallback: try first 10 chars (YYYY-MM-DD)
            try:
                parts = deadline[:10].split("-")
                if len(parts) == 3:
                    deadline = f"{parts[2]}/{parts[1]}/{parts[0]}"
            except Exception:
                pass
    if deadline:
        lines.append(f"📅 {deadline}")

    # Link -> use job URL fields
    link = (getattr(vaga, "link", None) or getattr(vaga, "jobUrl", None) or "").strip()
    if link:
        lines.append(f"🔗 Ver vaga: {link}")

    return "\n".join(lines)


def notify_new_vagas(vagas: List[Vaga]) -> int:
    """Send one message per vaga. Returns number of messages successfully sent."""
    sent = 0
    for vaga in vagas:
        text = _format_vaga_message(vaga)
        vaga_id = vaga.external_id if getattr(vaga, "external_id", None) else None
        if send_message(text, vaga_id=vaga_id):
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
