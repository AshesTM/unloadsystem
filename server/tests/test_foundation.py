"""Teste pentru fundatia noului server (DB, securitate, repositories)."""
import os, sys, tempfile, time

TMP = tempfile.mkdtemp()
os.environ["US_DATA_DIR"] = TMP
os.environ["US_BOOTSTRAP_ADMIN"] = "admin"
os.environ["US_BOOTSTRAP_PASSWORD"] = "BootStrap#123"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from unloadsystem import db, security, repositories as repo, protocol  # noqa

R = []
def check(name, cond):
    R.append((name, bool(cond)))
    print(("  OK  " if cond else " FAIL ") + name)

# ---- securitate ----
h = security.hash_password("parola-secreta")
check("hash incepe cu scrypt$", h.startswith("scrypt$"))
check("verify corect", security.verify_password("parola-secreta", h))
check("verify gresit", not security.verify_password("alta", h))
check("doua hash-uri difera (salt)", security.hash_password("x") != security.hash_password("x"))

# ---- init + migrations idempotent ----
v, created = db.init_db()
check("schema_version=1", v == 1)
check("bootstrap admin creat", created and created[0] == "admin")
v2, created2 = db.init_db()  # a doua oara
check("migrate idempotent", v2 == 1)
check("nu recreeaza adminul", created2 is None)

conn = db.connect()

# ---- roluri RBAC ----
roles = {r["name"]: r["rank"] for r in conn.execute("SELECT name,rank FROM roles").fetchall()}
check("4 roluri RBAC", set(roles) == {"super_admin", "admin", "technician", "read_only"})
check("super_admin rank cel mai mare", roles["super_admin"] == max(roles.values()))

# ---- login admin bootstrap ----
check("login admin corect", repo.verify_login(conn, "admin", "BootStrap#123") is not None)
check("login admin gresit", repo.verify_login(conn, "admin", "xx") is None)
adm = repo.user_by_username(conn, "admin")
check("admin e super_admin", adm["role_name"] == "super_admin")
check("admin must_change_pw", adm["must_change_pw"] == 1)

# ---- creare user + roluri ----
repo.create_user(conn, "tehnician1", "pass1234", role_name="technician")
check("tehnician creat", repo.user_by_username(conn, "tehnician1")["role_name"] == "technician")
check("login tehnician", repo.verify_login(conn, "tehnician1", "pass1234") is not None)
repo.set_password(conn, "tehnician1", "nouaParola9")
check("parola schimbata - vechea nu merge", repo.verify_login(conn, "tehnician1", "pass1234") is None)
check("parola schimbata - noua merge", repo.verify_login(conn, "tehnician1", "nouaParola9") is not None)

# ---- sesiuni auth + expirare ----
tok = repo.create_auth_session(conn, adm["id"], ttl_seconds=100, ip="1.2.3.4")
check("sesiune -> user", repo.user_for_auth_token(conn, tok)["username"] == "admin")
check("token invalid -> None", repo.user_for_auth_token(conn, "nope") is None)
tok_exp = repo.create_auth_session(conn, adm["id"], ttl_seconds=-1)
check("sesiune expirata -> None", repo.user_for_auth_token(conn, tok_exp) is None)
repo.delete_auth_session(conn, tok)
check("logout invalideaza", repo.user_for_auth_token(conn, tok) is None)

# ---- enrollment tokens ----
et = repo.create_enrollment_token(conn, created_by=adm["id"], note="PC client X", ttl_seconds=3600)
check("enroll token consumat o data", repo.consume_enrollment_token(conn, et, "dev-aaa"))
check("enroll token nu se reutilizeaza", not repo.consume_enrollment_token(conn, et, "dev-bbb"))
et2 = repo.create_enrollment_token(conn, ttl_seconds=-1)
check("enroll token expirat respins", not repo.consume_enrollment_token(conn, et2, "dev-ccc"))

# ---- machines (platform-agnostic + capabilities) ----
caps = {"remote_desktop": True, "remote_input": True, "multi_monitor": True,
        "clipboard": True, "file_transfer": True, "shell": False, "system_info": True}
m = repo.enroll_or_update_machine(conn, "dev-win-1", "PC-01", "Acme", "windows",
        "11 23H2", "3.0.0", "x64", "ACME-PC01", caps)
check("masina inrolata", m["device_id"] == "dev-win-1")
pub = repo.machine_public(conn, repo.get_machine(conn, "dev-win-1"), offline_after=30)
check("capabilities round-trip", pub["capabilities"]["file_transfer"] is True and pub["capabilities"]["shell"] is False)
check("platforma stocata", pub["platform"] == "windows")
check("online dupa enroll", pub["online"] is True)

# update acelasi device (nu dubleaza)
repo.enroll_or_update_machine(conn, "dev-win-1", "PC-01-ren", "Acme", "windows",
        "11 23H2", "3.1.0", "x64", "ACME-PC01", caps)
check("update nu dubleaza", len([x for x in repo.list_machines(conn) if x["device_id"]=="dev-win-1"]) == 1)
check("agent_version actualizat", repo.get_machine(conn, "dev-win-1")["agent_version"] == "3.1.0")

# o masina de alta platforma, capabilitati diferite
repo.enroll_or_update_machine(conn, "dev-android-1", "Telefon", "Acme", "android",
        "14", "1.0.0", "arm64", "pixel", protocol.default_caps_for("android"))
amac = repo.machine_public(conn, repo.get_machine(conn, "dev-android-1"), 30)
check("android fara file_transfer implicit", amac["capabilities"]["file_transfer"] is False)
check("android cu remote_desktop", amac["capabilities"]["remote_desktop"] is True)

# rename + delete
repo.rename_machine(conn, "dev-win-1", name="Server Principal", company="Datasol")
check("rename aplicat", repo.get_machine(conn, "dev-win-1")["company"] == "Datasol")
repo.delete_machine(conn, "dev-android-1")
check("delete masina", repo.get_machine(conn, "dev-android-1") is None)

# ---- audit ----
repo.audit(conn, "login", user=adm, ip="1.2.3.4")
repo.audit(conn, "connect", user=adm, target="dev-win-1")
check("audit are 2 intrari", len(repo.list_audit(conn)) == 2)
check("audit retine username", repo.list_audit(conn)[0]["username"] == "admin")

conn.close()
ok = sum(1 for _, c in R if c); tot = len(R)
print(f"\n==== {ok}/{tot} ====")
sys.exit(0 if ok == tot else 1)
