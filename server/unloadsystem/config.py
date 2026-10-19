"""
Configurare — totul din environment variables (fara secrete in cod).
Compatibil cross-platform; nimic Windows-specific.
"""
import os
import secrets

_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # server/


def _env(key, default=None):
    v = os.environ.get(key)
    return v if v not in (None, "") else default


class Config:
    # Retea
    HOST = _env("US_HOST", "0.0.0.0")
    PORT = int(_env("US_PORT", "8000"))

    # Bootstrap admin (doar la prima pornire, cu must_change_password=1)
    BOOTSTRAP_ADMIN_USER = _env("US_BOOTSTRAP_ADMIN", "admin")
    # Daca nu e dat prin env, generam o parola random si o scriem in bootstrap_password.txt.
    BOOTSTRAP_ADMIN_PASSWORD = _env("US_BOOTSTRAP_PASSWORD")  # None => random

    # Inrolare agenti.
    # Cheie partajata LEGACY (tranzitoriu, pt. agentii Python v3 existenti).
    # Gol => dezactivat. In productie se foloseste enrollment token per-dispozitiv.
    LEGACY_AGENT_KEY = _env("US_LEGACY_AGENT_KEY", "")
    ALLOW_LEGACY_KEY = _env("US_ALLOW_LEGACY_KEY", "1") == "1"

    # Sesiuni admin
    SESSION_TTL_SECONDS = int(_env("US_SESSION_TTL", str(12 * 3600)))

    # Rate limiting login
    LOGIN_MAX_FAILS = int(_env("US_LOGIN_MAX_FAILS", "8"))
    LOGIN_LOCK_SECONDS = int(_env("US_LOGIN_LOCK", "300"))

    # Offline dupa cate secunde fara heartbeat
    OFFLINE_AFTER = int(_env("US_OFFLINE_AFTER", "30"))

    # Cai de date (persistente, in afara codului)
    DATA_DIR = _env("US_DATA_DIR", os.path.join(_DIR, "data"))

    @property
    def db_path(self):
        os.makedirs(self.DATA_DIR, exist_ok=True)
        return _env("US_DB_PATH", os.path.join(self.DATA_DIR, "unloadsystem.db"))

    def resolved_bootstrap_password(self):
        """Parola de bootstrap: din env, sau una random scrisa pe disc o singura data."""
        if self.BOOTSTRAP_ADMIN_PASSWORD:
            return self.BOOTSTRAP_ADMIN_PASSWORD, False
        path = os.path.join(self.DATA_DIR, "bootstrap_password.txt")
        os.makedirs(self.DATA_DIR, exist_ok=True)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip(), False
        pw = secrets.token_urlsafe(12)
        with open(path, "w", encoding="utf-8") as f:
            f.write(pw)
        return pw, True


config = Config()
