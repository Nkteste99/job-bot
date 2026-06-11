from typing import List, Optional
import logging
import requests

from config.settings import settings
from models.models import Vaga


def _first_text(*values) -> Optional[str]:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


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
    company = _first_text(
        getattr(vaga, "companyName", None),
        getattr(vaga, "empresa", None),
        getattr(vaga, "careerPageName", None),
    )
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

    # Modalidade
    workplace = _first_text(
        getattr(vaga, "workplaceType", None),
        getattr(vaga, "workplace_type", None),
        getattr(vaga, "workplace", None),
        getattr(vaga, "modalidade", None),
        getattr(vaga, "modality", None),
    )
    workplace_value = (workplace or "").lower()
    if workplace_value == "remote":
        lines.append("🏠 Remoto")
    elif workplace_value == "hybrid":
        lines.append("🔄 Híbrido")
    elif workplace_value:
        lines.append("🏢 Presencial")

    # Salary placeholder for V3 extraction
    lines.append("⚠️ Salário: Não informado")

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
