"""Registru LIVE in memorie: conexiunile WS active (agent + vieweri).
Metadatele persistente stau in DB; aici doar conexiunile din momentul curent."""

# device_id -> {"ws": WS, "viewers": set(WS), "session_id": int|None}
AGENTS = {}


def agent_connected(device_id, ws):
    old = AGENTS.get(device_id)
    viewers = old["viewers"] if old else set()
    AGENTS[device_id] = {"ws": ws, "viewers": viewers, "session_id": None}
    return AGENTS[device_id]


def agent_disconnected(device_id, ws):
    a = AGENTS.get(device_id)
    if a and a["ws"] is ws:
        a["ws"] = None


def is_online(device_id):
    a = AGENTS.get(device_id)
    return bool(a and a["ws"] is not None)


def add_viewer(device_id, ws):
    a = AGENTS.get(device_id)
    if a is None:
        a = AGENTS.setdefault(device_id, {"ws": None, "viewers": set(), "session_id": None})
    a["viewers"].add(ws)
    return a


def remove_viewer(device_id, ws):
    a = AGENTS.get(device_id)
    if a:
        a["viewers"].discard(ws)


def viewer_count(device_id):
    a = AGENTS.get(device_id)
    return len(a["viewers"]) if a else 0
