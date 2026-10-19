"""
Handler HTTP + WebSocket (asyncio, stdlib) pe fundatia v4.
- Auth din DB (sesiuni cu expirare), RBAC, rate limiting.
- Enrollment agenti: enrollment token per-dispozitiv SAU cheie legacy (tranzitoriu).
- Relay pe canale (control/video/input/clipboard/files/system/events).
"""
import asyncio
import json
import time
from urllib.parse import urlparse, parse_qs

from .config import config
from . import db, repositories as repo, security, auth, live, protocol
from .ws import WS, accept_headers
from . import templates


# ===================== HTTP utils =====================
def parse_cookies(h):
    out = {}
    for part in h.get("cookie", "").split(";"):
        if "=" in part:
            k, v = part.strip().split("=", 1)
            out[k] = v
    return out


def http_response(status="200 OK", body=b"", ctype="text/html; charset=utf-8", extra=None):
    if isinstance(body, str):
        body = body.encode("utf-8")
    head = f"HTTP/1.1 {status}\r\nContent-Type: {ctype}\r\nContent-Length: {len(body)}\r\n"
    for k, v in (extra or {}).items():
        head += f"{k}: {v}\r\n"
    head += "Connection: close\r\n\r\n"
    return head.encode("utf-8") + body


def json_resp(obj, status="200 OK"):
    return http_response(status, json.dumps(obj), ctype="application/json")


def client_ip(headers, writer):
    ip = headers.get("cf-connecting-ip") or headers.get("x-forwarded-for", "").split(",")[0].strip()
    if ip:
        return ip
    try:
        return writer.get_extra_info("peername")[0]
    except Exception:
        return "?"


def current_user(conn, cookies):
    return repo.user_for_auth_token(conn, cookies.get("us_sess"))


# ===================== conexiune =====================
async def handle(reader, writer):
    try:
        line = await reader.readline()
        if not line:
            writer.close(); return
        parts = line.decode("latin1").split()
        if len(parts) < 2:
            writer.close(); return
        method, target = parts[0], parts[1]
        headers = {}
        while True:
            h = await reader.readline()
            if h in (b"\r\n", b"", b"\n"):
                break
            k, _, v = h.decode("latin1").partition(":")
            headers[k.strip().lower()] = v.strip()
        path = urlparse(target).path
        cookies = parse_cookies(headers)
        ip = client_ip(headers, writer)

        if headers.get("upgrade", "").lower() == "websocket":
            key = headers.get("sec-websocket-key", "")
            writer.write(accept_headers(key).encode()); await writer.drain()
            ws = WS(reader, writer, is_server=True)
            if path == "/agent-ws":
                await ws_agent(ws, ip)
            elif path.startswith("/view-ws/"):
                await ws_view(ws, path.split("/view-ws/", 1)[1], cookies, ip)
            else:
                await ws.close()
            return

        body = b""
        if method == "POST":
            n = int(headers.get("content-length", "0") or 0)
            if n:
                body = await reader.readexactly(n)

        resp = route_http(method, path, headers, cookies, body, ip)
        writer.write(resp); await writer.drain()
    except (ConnectionError, asyncio.IncompleteReadError):
        pass
    finally:
        try:
            writer.close()
        except Exception:
            pass


def _form(body):
    return {k: v[0] for k, v in parse_qs(body.decode("utf-8", "replace")).items()}


def _jbody(body):
    try:
        return json.loads(body.decode("utf-8", "replace") or "{}")
    except Exception:
        return {}


# ===================== routing HTTP =====================
def route_http(method, path, headers, cookies, body, ip):
    conn = db.connect()
    try:
        # ---- login ----
        if path == "/login" and method == "GET":
            return http_response(body=templates.LOGIN_HTML)
        if path == "/login" and method == "POST":
            if not auth.login_allowed(ip, config.LOGIN_MAX_FAILS, config.LOGIN_LOCK_SECONDS):
                return http_response(body=templates.LOGIN_HTML.replace(
                    "<!--ERR-->", '<div class="err">Prea multe incercari. Asteapta cateva minute.</div>'))
            form = _form(body)
            u = repo.verify_login(conn, form.get("user", ""), form.get("password", ""))
            if u:
                auth.login_ok(ip)
                tok = repo.create_auth_session(conn, u["id"], config.SESSION_TTL_SECONDS, ip)
                repo.audit(conn, "login", user=u, ip=ip)
                return http_response("302 Found", b"", extra={
                    "Location": "/", "Set-Cookie": f"us_sess={tok}; HttpOnly; SameSite=Lax; Path=/"})
            auth.login_failed(ip, config.LOGIN_MAX_FAILS, config.LOGIN_LOCK_SECONDS)
            repo.audit(conn, "login_fail", target=form.get("user", ""), ip=ip)
            return http_response(body=templates.LOGIN_HTML.replace(
                "<!--ERR-->", '<div class="err">User sau parola gresita.</div>'))
        if path == "/logout":
            repo.delete_auth_session(conn, cookies.get("us_sess"))
            return http_response("302 Found", b"", extra={
                "Location": "/login", "Set-Cookie": "us_sess=; Path=/; Max-Age=0"})

        me = current_user(conn, cookies)

        # ---- schimbare parola (fortat sau voluntar) ----
        if path == "/change-password" and method == "GET":
            if not me:
                return http_response("302 Found", b"", extra={"Location": "/login"})
            return http_response(body=templates.CHANGEPW_HTML)
        if path == "/change-password" and method == "POST":
            if not me:
                return json_resp({"error": "auth"}, "403 Forbidden")
            d = _jbody(body)
            if not security.verify_password(d.get("old", ""), me["password"]):
                return json_resp({"error": "Parola veche gresita."}, "400 Bad Request")
            if len(d.get("new", "")) < 6:
                return json_resp({"error": "Parola noua prea scurta (min 6)."}, "400 Bad Request")
            repo.set_password(conn, me["username"], d["new"])
            repo.audit(conn, "change_password", user=me, ip=ip)
            return json_resp({"ok": True})

        # ---- consola ----
        if path == "/":
            if not me:
                return http_response("302 Found", b"", extra={"Location": "/login"})
            if me["must_change_pw"]:
                return http_response("302 Found", b"", extra={"Location": "/change-password"})
            return http_response(body=templates.CONSOLE_HTML
                                 .replace("__USER__", me["username"])
                                 .replace("__ROLE__", me["role_name"]))

        # ---- API ----
        if path.startswith("/api/"):
            if not me:
                return json_resp({"error": "auth"}, "403 Forbidden")
            return route_api(conn, path, method, body, me, ip)

        # ---- view ----
        if path.startswith("/view/"):
            if not me:
                return http_response("302 Found", b"", extra={"Location": "/login"})
            if not auth.can(me, "remote_control"):
                return http_response("403 Forbidden", b"Nu ai dreptul de remote control.")
            device_id = path.split("/view/", 1)[1]
            m = repo.get_machine(conn, device_id)
            if not m:
                return http_response("404 Not Found", b"inexistent")
            html = (templates.VIEW_HTML.replace("__DID__", device_id)
                    .replace("__NAME__", m["name"])
                    .replace("__CAPS__", json.dumps(db.caps_from_json(m["capabilities"]))))
            return http_response(body=html)

        return http_response("404 Not Found", b"not found")
    finally:
        conn.close()


def route_api(conn, path, method, body, me, ip):
    # ----- machines -----
    if path == "/api/machines":
        rows = [repo.machine_public(conn, m, config.OFFLINE_AFTER) for m in repo.list_machines(conn)]
        for r in rows:
            r["online"] = live.is_online(r["device_id"])
        return json_resp({"machines": rows, "me": me["username"], "role": me["role_name"]})
    if path == "/api/machines/rename" and method == "POST":
        if not auth.can(me, "manage_machines"):
            return json_resp({"error": "fara drept"}, "403 Forbidden")
        d = _jbody(body)
        if repo.rename_machine(conn, d.get("device_id"), d.get("name"), d.get("company"), d.get("notes")):
            repo.audit(conn, "rename_machine", user=me, target=d.get("device_id"), ip=ip)
            return json_resp({"ok": True})
        return json_resp({"error": "inexistent"}, "404 Not Found")
    if path == "/api/machines/del" and method == "POST":
        if not auth.can(me, "manage_machines"):
            return json_resp({"error": "fara drept"}, "403 Forbidden")
        d = _jbody(body)
        a = live.AGENTS.get(d.get("device_id"))
        if a and a.get("ws"):
            try:
                asyncio.create_task(a["ws"].close())
            except Exception:
                pass
        repo.delete_machine(conn, d.get("device_id"))
        repo.audit(conn, "delete_machine", user=me, target=d.get("device_id"), ip=ip)
        return json_resp({"ok": True})

    # ----- users (RBAC) -----
    if path == "/api/users":
        if not auth.can(me, "manage_users"):
            return json_resp({"error": "fara drept"}, "403 Forbidden")
        return json_resp({"users": [dict(u) for u in repo.list_users(conn)], "me": me["username"]})
    if path == "/api/users/add" and method == "POST":
        if not auth.can(me, "manage_users"):
            return json_resp({"error": "fara drept"}, "403 Forbidden")
        d = _jbody(body)
        u, p, role = (d.get("user") or "").strip(), d.get("password") or "", d.get("role") or "technician"
        if not u or len(p) < 6:
            return json_resp({"error": "User gol sau parola prea scurta (min 6)."}, "400 Bad Request")
        if role not in ("read_only", "technician", "admin", "super_admin"):
            return json_resp({"error": "rol invalid"}, "400 Bad Request")
        # nu poti crea un rol mai mare decat al tau
        rank = {"read_only": 10, "technician": 40, "admin": 70, "super_admin": 100}[role]
        if rank > me["role_rank"]:
            return json_resp({"error": "Nu poti crea un rol mai mare decat al tau."}, "400 Bad Request")
        if repo.user_by_username(conn, u):
            return json_resp({"error": "Exista deja."}, "400 Bad Request")
        repo.create_user(conn, u, p, role_name=role, must_change=True)
        repo.audit(conn, "add_user", user=me, target=u, detail=role, ip=ip)
        return json_resp({"ok": True})
    if path == "/api/users/del" and method == "POST":
        if not auth.can(me, "manage_users"):
            return json_resp({"error": "fara drept"}, "403 Forbidden")
        d = _jbody(body); target = (d.get("user") or "").strip()
        if target == me["username"]:
            return json_resp({"error": "Nu te poti sterge pe tine."}, "400 Bad Request")
        tu = repo.user_by_username(conn, target)
        if not tu:
            return json_resp({"error": "inexistent"}, "404 Not Found")
        if tu["role_rank"] >= me["role_rank"] and me["role_name"] != "super_admin":
            return json_resp({"error": "Nu poti sterge un cont cu rol egal/mai mare."}, "400 Bad Request")
        if repo.count_users(conn) <= 1:
            return json_resp({"error": "Nu poti sterge ultimul cont."}, "400 Bad Request")
        repo.delete_user(conn, target)
        repo.audit(conn, "delete_user", user=me, target=target, ip=ip)
        return json_resp({"ok": True})
    if path == "/api/users/passwd" and method == "POST":
        if not auth.can(me, "manage_users"):
            return json_resp({"error": "fara drept"}, "403 Forbidden")
        d = _jbody(body); target = (d.get("user") or "").strip()
        if len(d.get("password", "")) < 6:
            return json_resp({"error": "Parola prea scurta (min 6)."}, "400 Bad Request")
        if not repo.user_by_username(conn, target):
            return json_resp({"error": "inexistent"}, "404 Not Found")
        repo.set_password(conn, target, d["password"], clear_must_change=False)
        repo.audit(conn, "reset_password", user=me, target=target, ip=ip)
        return json_resp({"ok": True})

    # ----- enrollment tokens -----
    if path == "/api/enroll-tokens" and method == "GET":
        if not auth.can(me, "manage_enroll"):
            return json_resp({"error": "fara drept"}, "403 Forbidden")
        rows = conn.execute("SELECT token,note,created_at,expires_at,used_at,used_by_device "
                            "FROM enrollment_tokens ORDER BY created_at DESC LIMIT 100").fetchall()
        return json_resp({"tokens": [dict(r) for r in rows]})
    if path == "/api/enroll-tokens/create" and method == "POST":
        if not auth.can(me, "manage_enroll"):
            return json_resp({"error": "fara drept"}, "403 Forbidden")
        d = _jbody(body)
        ttl = int(d.get("ttl_hours", 0)) * 3600 or None
        tok = repo.create_enrollment_token(conn, created_by=me["id"], note=d.get("note", ""), ttl_seconds=ttl)
        repo.audit(conn, "create_enroll_token", user=me, ip=ip)
        return json_resp({"ok": True, "token": tok})

    # ----- audit -----
    if path == "/api/audit":
        if not auth.can(me, "view_audit"):
            return json_resp({"error": "fara drept"}, "403 Forbidden")
        return json_resp({"logs": [dict(r) for r in repo.list_audit(conn, 200)]})

    return json_resp({"error": "not found"}, "404 Not Found")


# ===================== WS: agent =====================
def _authenticate_agent(conn, msg):
    """Returneaza True daca agentul are voie sa se inroleze."""
    device_id = msg.get("device_id")
    token = msg.get("enroll_token")
    if token:
        return repo.consume_enrollment_token(conn, token, device_id)
    if config.ALLOW_LEGACY_KEY and config.LEGACY_AGENT_KEY:
        return security.constant_eq(msg.get("key", ""), config.LEGACY_AGENT_KEY)
    return False


async def _set_watch(entry):
    if entry["ws"] is not None:
        on = len(entry["viewers"]) > 0
        await entry["ws"].send_text(protocol.dumps(protocol.CH_CONTROL, "watch", on=on))


async def ws_agent(ws, ip):
    device_id = None
    conn = db.connect()
    try:
        while True:
            kind, data = await ws.recv()
            if kind == "close":
                break
            if kind == "binary":
                # cadre video -> toti viewerii
                if device_id and device_id in live.AGENTS:
                    repo.touch_machine(conn, device_id)
                    for v in list(live.AGENTS[device_id]["viewers"]):
                        await v.send_bytes(data)
                continue
            ch, t, msg = protocol.parse(data)
            if ch is None:
                continue
            if ch == protocol.CH_CONTROL and t == "hello":
                if not _authenticate_agent(conn, msg):
                    await ws.send_text(protocol.dumps(protocol.CH_CONTROL, "denied"))
                    break
                device_id = msg.get("device_id") or security.new_device_id()
                caps = protocol.normalize_caps(msg.get("capabilities"))
                repo.enroll_or_update_machine(
                    conn, device_id,
                    name=msg.get("name") or msg.get("hostname") or device_id,
                    company=msg.get("company", ""),
                    platform=msg.get("platform", "unknown"),
                    platform_version=msg.get("platform_version", ""),
                    agent_version=msg.get("agent_version", ""),
                    architecture=msg.get("architecture", ""),
                    hostname=msg.get("hostname", ""),
                    capabilities=caps)
                entry = live.agent_connected(device_id, ws)
                repo.audit(conn, "agent_online", target=device_id, ip=ip)
                await ws.send_text(protocol.dumps(protocol.CH_CONTROL, "ok", device_id=device_id))
                await _set_watch(entry)
            elif device_id and device_id in live.AGENTS:
                repo.touch_machine(conn, device_id)
                # orice alt mesaj al agentului -> viewerii (ls-res, dl-*, monitors, info, etc.)
                for v in list(live.AGENTS[device_id]["viewers"]):
                    await v.send_text(data)
    finally:
        if device_id:
            live.agent_disconnected(device_id, ws)
            try:
                repo.audit(conn, "agent_offline", target=device_id, ip=ip)
            except Exception:
                pass
        conn.close()
        await ws.close()


# ===================== WS: viewer =====================
async def ws_view(ws, device_id, cookies, ip):
    conn = db.connect()
    try:
        me = current_user(conn, cookies)
        if not me or not auth.can(me, "remote_control"):
            await ws.close(); return
        m = repo.get_machine(conn, device_id)
        if not m:
            await ws.close(); return
        entry = live.add_viewer(device_id, ws)
        # session history
        rs = conn.execute("INSERT INTO remote_sessions(machine_id,user_id,started_at,client_ip) "
                          "VALUES ((SELECT id FROM machines WHERE device_id=?),?,?,?)",
                          (device_id, me["id"], time.time(), ip))
        conn.commit()
        session_id = rs.lastrowid
        repo.audit(conn, "connect", user=me, target=device_id, ip=ip)
        await _set_watch(entry)
        # trimite capabilitatile masinii viewerului
        await ws.send_text(protocol.dumps(protocol.CH_CONTROL, "caps",
                                          capabilities=db.caps_from_json(m["capabilities"])))
        try:
            while True:
                kind, data = await ws.recv()
                if kind == "close":
                    break
                if kind == "text":
                    a = live.AGENTS.get(device_id)
                    if a and a["ws"] is not None:
                        await a["ws"].send_text(data)
        finally:
            live.remove_viewer(device_id, ws)
            conn.execute("UPDATE remote_sessions SET ended_at=? WHERE id=?", (time.time(), session_id))
            conn.commit()
            a = live.AGENTS.get(device_id)
            if a:
                await _set_watch(a)
    finally:
        conn.close()
        await ws.close()


# ===================== entrypoint =====================
async def serve():
    ver, created = db.init_db()
    print(f"[*] UnloadSystems Remote server v4 — schema v{ver} — http://localhost:{config.PORT}")
    if created:
        user, pw, generated = created
        where = "(generata, in data/bootstrap_password.txt)" if generated else "(din env)"
        print(f"[*] Admin de bootstrap: {user} / {pw} {where}  — se cere schimbarea la primul login")
    server = await asyncio.start_server(handle, config.HOST, config.PORT)
    async with server:
        await server.serve_forever()


def main():
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        pass
