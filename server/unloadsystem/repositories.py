"""
Repository layer — singurul loc care atinge SQL. Restul aplicatiei foloseste
aceste functii. (Inlocuibil ulterior cu SQLAlchemy fara a schimba apelantii.)
"""
import time

from .db import connect, caps_to_json, caps_from_json
from . import security, protocol


# ===================== USERS =====================
def user_by_username(conn, username):
    return conn.execute(
        "SELECT u.*, r.name AS role_name, r.rank AS role_rank "
        "FROM users u JOIN roles r ON r.id=u.role_id WHERE u.username=?",
        (username,)).fetchone()


def user_by_id(conn, uid):
    return conn.execute(
        "SELECT u.*, r.name AS role_name, r.rank AS role_rank "
        "FROM users u JOIN roles r ON r.id=u.role_id WHERE u.id=?", (uid,)).fetchone()


def create_user(conn, username, password, role_name="technician", must_change=False):
    role = conn.execute("SELECT id FROM roles WHERE name=?", (role_name,)).fetchone()
    if not role:
        raise ValueError("rol inexistent: %s" % role_name)
    conn.execute("INSERT INTO users(username, password, role_id, active, must_change_pw, created_at) "
                 "VALUES (?,?,?,1,?,?)",
                 (username, security.hash_password(password), role["id"],
                  1 if must_change else 0, time.time()))
    conn.commit()
    return user_by_username(conn, username)


def set_password(conn, username, password, clear_must_change=True):
    conn.execute("UPDATE users SET password=?, must_change_pw=? WHERE username=?",
                 (security.hash_password(password), 0 if clear_must_change else 1, username))
    conn.commit()


def verify_login(conn, username, password):
    u = user_by_username(conn, username)
    if not u or not u["active"]:
        return None
    if security.verify_password(password, u["password"]):
        conn.execute("UPDATE users SET last_login=? WHERE id=?", (time.time(), u["id"]))
        conn.commit()
        return u
    return None


def list_users(conn):
    return conn.execute(
        "SELECT u.id,u.username,u.active,u.must_change_pw,u.last_login,r.name AS role_name "
        "FROM users u JOIN roles r ON r.id=u.role_id ORDER BY u.username").fetchall()


def delete_user(conn, username):
    conn.execute("DELETE FROM users WHERE username=?", (username,))
    conn.commit()


def count_users(conn):
    return conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]


# ===================== AUTH SESSIONS =====================
def create_auth_session(conn, user_id, ttl_seconds, ip=None):
    tok = security.new_token()
    now = time.time()
    conn.execute("INSERT INTO auth_sessions(token,user_id,created_at,expires_at,last_seen,ip) "
                 "VALUES (?,?,?,?,?,?)", (tok, user_id, now, now + ttl_seconds, now, ip))
    conn.commit()
    return tok


def user_for_auth_token(conn, token):
    if not token:
        return None
    row = conn.execute("SELECT * FROM auth_sessions WHERE token=?", (token,)).fetchone()
    if not row:
        return None
    if row["expires_at"] < time.time():
        conn.execute("DELETE FROM auth_sessions WHERE token=?", (token,))
        conn.commit()
        return None
    conn.execute("UPDATE auth_sessions SET last_seen=? WHERE token=?", (time.time(), token))
    conn.commit()
    return user_by_id(conn, row["user_id"])


def delete_auth_session(conn, token):
    conn.execute("DELETE FROM auth_sessions WHERE token=?", (token,))
    conn.commit()


def cleanup_auth_sessions(conn):
    conn.execute("DELETE FROM auth_sessions WHERE expires_at < ?", (time.time(),))
    conn.commit()


# ===================== ENROLLMENT TOKENS =====================
def create_enrollment_token(conn, created_by=None, note="", ttl_seconds=None):
    tok = security.new_token(20)
    now = time.time()
    exp = now + ttl_seconds if ttl_seconds else None
    conn.execute("INSERT INTO enrollment_tokens(token,note,created_by,created_at,expires_at) "
                 "VALUES (?,?,?,?,?)", (tok, note, created_by, now, exp))
    conn.commit()
    return tok


def consume_enrollment_token(conn, token, device_id):
    row = conn.execute("SELECT * FROM enrollment_tokens WHERE token=?", (token,)).fetchone()
    if not row:
        return False
    if row["used_at"] is not None:
        return False
    if row["expires_at"] is not None and row["expires_at"] < time.time():
        return False
    conn.execute("UPDATE enrollment_tokens SET used_at=?, used_by_device=? WHERE token=?",
                 (time.time(), device_id, token))
    conn.commit()
    return True


# ===================== MACHINES =====================
def enroll_or_update_machine(conn, device_id, name, company, platform, platform_version,
                             agent_version, architecture, hostname, capabilities):
    now = time.time()
    existing = conn.execute("SELECT id FROM machines WHERE device_id=?", (device_id,)).fetchone()
    caps_json = caps_to_json(capabilities)
    if existing:
        conn.execute(
            "UPDATE machines SET name=?, company=?, platform=?, platform_version=?, "
            "agent_version=?, architecture=?, hostname=?, capabilities=?, last_seen=? "
            "WHERE device_id=?",
            (name, company, platform, platform_version, agent_version, architecture,
             hostname, caps_json, now, device_id))
    else:
        conn.execute(
            "INSERT INTO machines(device_id,name,company,platform,platform_version,"
            "agent_version,architecture,hostname,capabilities,last_seen,enrolled_at,created_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (device_id, name, company, platform, platform_version, agent_version,
             architecture, hostname, caps_json, now, now, now))
    conn.commit()
    return conn.execute("SELECT * FROM machines WHERE device_id=?", (device_id,)).fetchone()


def touch_machine(conn, device_id):
    conn.execute("UPDATE machines SET last_seen=? WHERE device_id=?", (time.time(), device_id))
    conn.commit()


def get_machine(conn, device_id):
    return conn.execute("SELECT * FROM machines WHERE device_id=?", (device_id,)).fetchone()


def list_machines(conn):
    return conn.execute("SELECT * FROM machines ORDER BY company, name").fetchall()


def rename_machine(conn, device_id, name=None, company=None, notes=None):
    m = get_machine(conn, device_id)
    if not m:
        return False
    conn.execute("UPDATE machines SET name=?, company=?, notes=? WHERE device_id=?",
                 (name if name is not None else m["name"],
                  company if company is not None else m["company"],
                  notes if notes is not None else m["notes"], device_id))
    conn.commit()
    return True


def delete_machine(conn, device_id):
    conn.execute("DELETE FROM machines WHERE device_id=?", (device_id,))
    conn.commit()


def machine_public(conn, m, offline_after):
    """Reprezentare pentru consola, cu capabilities decodate si online calculat."""
    online = (time.time() - m["last_seen"]) < offline_after
    return {
        "device_id": m["device_id"], "name": m["name"],
        "company": m["company"] or "Fara grup", "platform": m["platform"],
        "platform_version": m["platform_version"], "agent_version": m["agent_version"],
        "architecture": m["architecture"], "hostname": m["hostname"],
        "capabilities": caps_from_json(m["capabilities"]),
        "last_seen": m["last_seen"], "online": online,
    }


# ===================== AUDIT =====================
def audit(conn, action, user=None, target=None, detail=None, ip=None):
    conn.execute("INSERT INTO audit_logs(ts,user_id,username,action,target,detail,ip) "
                 "VALUES (?,?,?,?,?,?,?)",
                 (time.time(), user["id"] if user else None,
                  user["username"] if user else None, action, target, detail, ip))
    conn.commit()


def list_audit(conn, limit=200):
    return conn.execute("SELECT * FROM audit_logs ORDER BY ts DESC LIMIT ?", (limit,)).fetchall()
