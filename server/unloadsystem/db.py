"""
Baza de date — sqlite3 (stdlib), cu migrations versionate.
Schema PLATFORM-AGNOSTICA: un singur tabel `machines` cu coloana `platform`
si `capabilities` (JSON). Fara tabele per-platforma.
Interfata subtire ca sa poata fi inlocuita ulterior cu SQLAlchemy/Postgres.
"""
import json
import sqlite3
import time

from .config import config
from . import security
from . import protocol

# ---- Migrations: lista ordonata de (versiune, SQL). Nu modifica cele existente. ----
MIGRATIONS = [
    (1, """
    CREATE TABLE roles (
        id INTEGER PRIMARY KEY,
        name TEXT UNIQUE NOT NULL,
        rank INTEGER NOT NULL
    );
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role_id INTEGER NOT NULL REFERENCES roles(id),
        active INTEGER NOT NULL DEFAULT 1,
        must_change_pw INTEGER NOT NULL DEFAULT 0,
        created_at REAL NOT NULL,
        last_login REAL
    );
    CREATE TABLE machines (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        company TEXT NOT NULL DEFAULT '',
        platform TEXT NOT NULL DEFAULT 'unknown',
        platform_version TEXT NOT NULL DEFAULT '',
        agent_version TEXT NOT NULL DEFAULT '',
        architecture TEXT NOT NULL DEFAULT '',
        hostname TEXT NOT NULL DEFAULT '',
        capabilities TEXT NOT NULL DEFAULT '{}',
        notes TEXT NOT NULL DEFAULT '',
        last_seen REAL NOT NULL DEFAULT 0,
        enrolled_at REAL,
        created_at REAL NOT NULL
    );
    CREATE TABLE machine_tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        machine_id INTEGER NOT NULL REFERENCES machines(id) ON DELETE CASCADE,
        tag TEXT NOT NULL
    );
    CREATE TABLE enrollment_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        token TEXT UNIQUE NOT NULL,
        note TEXT NOT NULL DEFAULT '',
        created_by INTEGER REFERENCES users(id),
        created_at REAL NOT NULL,
        expires_at REAL,
        used_at REAL,
        used_by_device TEXT
    );
    CREATE TABLE auth_sessions (
        token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        created_at REAL NOT NULL,
        expires_at REAL NOT NULL,
        last_seen REAL NOT NULL,
        ip TEXT
    );
    CREATE TABLE remote_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        machine_id INTEGER NOT NULL REFERENCES machines(id) ON DELETE CASCADE,
        user_id INTEGER REFERENCES users(id),
        started_at REAL NOT NULL,
        ended_at REAL,
        client_ip TEXT
    );
    CREATE TABLE session_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        remote_session_id INTEGER NOT NULL REFERENCES remote_sessions(id) ON DELETE CASCADE,
        ts REAL NOT NULL,
        type TEXT NOT NULL,
        detail TEXT NOT NULL DEFAULT ''
    );
    CREATE TABLE file_transfers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        remote_session_id INTEGER REFERENCES remote_sessions(id) ON DELETE SET NULL,
        machine_id INTEGER REFERENCES machines(id) ON DELETE SET NULL,
        direction TEXT NOT NULL,
        filename TEXT NOT NULL,
        size INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'started',
        ts REAL NOT NULL
    );
    CREATE TABLE audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts REAL NOT NULL,
        user_id INTEGER,
        username TEXT,
        action TEXT NOT NULL,
        target TEXT,
        detail TEXT,
        ip TEXT
    );
    CREATE TABLE agent_versions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel TEXT NOT NULL,
        version TEXT NOT NULL,
        url TEXT NOT NULL DEFAULT '',
        checksum TEXT NOT NULL DEFAULT '',
        signature TEXT NOT NULL DEFAULT '',
        published_at REAL NOT NULL,
        notes TEXT NOT NULL DEFAULT ''
    );
    CREATE TABLE settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    );
    CREATE INDEX idx_machines_company ON machines(company);
    CREATE INDEX idx_audit_ts ON audit_logs(ts);
    CREATE INDEX idx_remote_sessions_machine ON remote_sessions(machine_id);
    """),
]

# Roluri RBAC (rank mai mare = mai multe drepturi)
ROLES = [("super_admin", 100), ("admin", 70), ("technician", 40), ("read_only", 10)]


def connect():
    conn = sqlite3.connect(config.db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _schema_version(conn):
    conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
    row = conn.execute("SELECT MAX(version) AS v FROM schema_version").fetchone()
    return row["v"] or 0


def migrate(conn=None):
    own = conn is None
    conn = conn or connect()
    try:
        cur = _schema_version(conn)
        for version, sql in MIGRATIONS:
            if version > cur:
                conn.executescript(sql)
                conn.execute("INSERT INTO schema_version(version) VALUES (?)", (version,))
                conn.commit()
        return _schema_version(conn)
    finally:
        if own:
            conn.close()


def seed(conn=None):
    """Roluri + admin de bootstrap (must_change_pw=1). Idempotent."""
    own = conn is None
    conn = conn or connect()
    try:
        for name, rank in ROLES:
            conn.execute("INSERT OR IGNORE INTO roles(name, rank) VALUES (?, ?)", (name, rank))
        conn.commit()
        # admin de bootstrap doar daca nu exista niciun user
        n = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
        created = None
        if n == 0:
            pw, generated = config.resolved_bootstrap_password()
            role = conn.execute("SELECT id FROM roles WHERE name='super_admin'").fetchone()
            conn.execute("INSERT INTO users(username, password, role_id, active, "
                         "must_change_pw, created_at) VALUES (?,?,?,1,1,?)",
                         (config.BOOTSTRAP_ADMIN_USER, security.hash_password(pw),
                          role["id"], time.time()))
            conn.commit()
            created = (config.BOOTSTRAP_ADMIN_USER, pw, generated)
        return created
    finally:
        if own:
            conn.close()


def init_db():
    """Migrate + seed. Returneaza (schema_version, bootstrap_info|None)."""
    conn = connect()
    try:
        v = migrate(conn)
        created = seed(conn)
        return v, created
    finally:
        conn.close()


# ---- helper JSON pentru capabilities ----
def caps_to_json(caps):
    return json.dumps(protocol.normalize_caps(caps))


def caps_from_json(s):
    try:
        return protocol.normalize_caps(json.loads(s))
    except Exception:
        return protocol.normalize_caps({})
