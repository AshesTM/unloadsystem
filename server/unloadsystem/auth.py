"""RBAC (ranguri) + rate limiting login (in memorie)."""
import time

# Praguri de rang pentru actiuni
RANK_READ_ONLY = 10
RANK_TECHNICIAN = 40
RANK_ADMIN = 70
RANK_SUPER = 100

# Ce rang minim cere fiecare actiune
PERM = {
    "view_machines": RANK_READ_ONLY,
    "remote_control": RANK_TECHNICIAN,
    "file_transfer": RANK_TECHNICIAN,
    "manage_machines": RANK_ADMIN,      # rename/delete masini
    "manage_enroll": RANK_ADMIN,        # enrollment tokens
    "view_audit": RANK_ADMIN,
    "manage_users": RANK_ADMIN,
}


def can(user, action):
    if not user:
        return False
    need = PERM.get(action, RANK_SUPER)
    return user["role_rank"] >= need


# ---- rate limiting login per IP ----
_fails = {}  # ip -> [count, locked_until]


def login_allowed(ip, max_fails, lock_seconds):
    rec = _fails.get(ip)
    if not rec:
        return True
    count, locked_until = rec
    if locked_until and time.time() < locked_until:
        return False
    return True


def login_failed(ip, max_fails, lock_seconds):
    count, locked_until = _fails.get(ip, [0, 0])
    count += 1
    if count >= max_fails:
        locked_until = time.time() + lock_seconds
        count = 0
    _fails[ip] = [count, locked_until]


def login_ok(ip):
    _fails.pop(ip, None)
