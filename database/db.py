"""Supabase client initializer.

Provides a small, safe wrapper around the `supabase` client used by the
project. Initialization is defensive so importing this module won't crash if
environment variables are missing or the `supabase` package is not installed.

Use `db.client` to access the underlying client and `db.test_connection()` to
perform a lightweight connectivity check.
"""
from typing import Optional

import httpx

from config.settings import settings

try:
    from supabase import create_client
except Exception:  # pragma: no cover - provide a helpful import-time message
    create_client = None


class Database:
    def __init__(self):
        self.supabase_url: Optional[str] = None
        self.supabase_key: Optional[str] = None
        self.client = None

        try:
            self.supabase_url = str(settings.SUPABASE_URL)
            # settings.SUPABASE_KEY is a SecretStr
            self.supabase_key = settings.SUPABASE_KEY.get_secret_value()
        except Exception:
            # settings may not be configured in some contexts (tests, linting)
            self.supabase_url = None
            self.supabase_key = None

        if create_client is not None and self.supabase_url and self.supabase_key:
            try:
                self.client = create_client(self.supabase_url, self.supabase_key)
            except Exception:
                self.client = None

    def ping(self) -> bool:
        """Lightweight check that configuration values exist."""
        return bool(self.supabase_url and self.supabase_key)

    def test_connection(self, timeout: float = 5.0) -> bool:
        """Test connectivity to the Supabase PostgREST endpoint.

        This does not require any specific table to exist; it performs a
        GET request against the PostgREST root (`/rest/v1`) using the
        configured key. If the HTTP response is received and is not a 5xx
        server error, we consider the connection attempt successful.
        """
        if not (self.supabase_url and self.supabase_key):
            return False

        url = self.supabase_url.rstrip("/") + "/rest/v1"
        headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
        }

        try:
            resp = httpx.get(url, headers=headers, timeout=timeout)
            return resp.status_code < 500
        except Exception:
            return False


db = Database()


if __name__ == "__main__":
    ok = db.test_connection()
    print("Supabase configured:", db.ping())
    print("Supabase reachable:", ok)


def test_connection() -> bool:
    """Module-level helper: ensure client exists and perform a simple query.

    Returns True if the Supabase client can be initialized and a lightweight
    query against the `vagas` table completes without raising an exception.
    """
    # initialize client if not present
    if db.client is None:
        if create_client is None or not (db.supabase_url and db.supabase_key):
            print("❌ Falha na conexão: cliente Supabase não configurado")
            return False
        try:
            db.client = create_client(db.supabase_url, db.supabase_key)
        except Exception as e:
            print(f"❌ Falha na conexão: {e}")
            return False

    try:
        result = db.client.table("vagas").select("id").limit(1).execute()
        print("✅ Conexão com Supabase OK")
        return True
    except Exception as e:
        print(f"❌ Falha na conexão: {e}")
        return False
