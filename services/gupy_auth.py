import requests
from datetime import datetime, timezone
import base64
import json

from config.settings import settings
from notifier.telegram import send_message

GUPY_ORIGIN = "https://spread.gupy.io"
GUPY_USER_AGENT = "Mozilla/5.0"
CURRENT_ACCOUNT_URL = (
    "https://private-api.gupy.io/authentication/candidate/account/current"
)


def get_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "cookie": f"candidate_secure_token={settings.GUPY_COOKIE.get_secret_value()}",
            "origin": GUPY_ORIGIN,
            "user-agent": GUPY_USER_AGENT,
        }
    )
    return session


def check_auth(session: requests.Session) -> bool:
    response = session.get(CURRENT_ACCOUNT_URL, timeout=30)
    return response.status_code == 200


def get_cookie_expiry() -> datetime | None:
    """Decodifica o JWT e retorna a data de expiração."""
    try:
        token = settings.GUPY_COOKIE.get_secret_value()
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        decoded = json.loads(base64.urlsafe_b64decode(payload))
        exp = decoded.get("exp")
        if exp:
            return datetime.fromtimestamp(exp, tz=timezone.utc)
    except Exception:
        pass
    return None


def check_cookie_expiry_and_notify() -> None:
    """Verifica se o cookie vai expirar em breve e notifica no Telegram."""
    expiry = get_cookie_expiry()
    if not expiry:
        send_message("⚠️ Job Bot: não foi possível verificar a expiração do cookie da Gupy.")
        return

    now = datetime.now(tz=timezone.utc)
    days_left = (expiry - now).days

    if days_left <= 0:
        send_message("🔴 Job Bot: cookie da Gupy EXPIRADO! Faça login novamente e atualize o GUPY_COOKIE no .env.")
    elif days_left <= 3:
        send_message(f"🟠 Job Bot: cookie da Gupy expira em {days_left} dia(s)! Renove em breve.")
    elif days_left <= 7:
        send_message(f"🟡 Job Bot: cookie da Gupy expira em {days_left} dias.")