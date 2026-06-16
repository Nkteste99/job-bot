import requests

from config.settings import settings

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
