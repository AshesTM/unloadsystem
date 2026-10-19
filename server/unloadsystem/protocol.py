"""
Protocol comun, platform-agnostic.
Mesajele circula ca JSON cu un envelope: {"ch": <canal>, "t": <tip>, ...}
Nu exista mesaje specifice unei platforme in protocolul comun.
"""
import json

PROTOCOL_VERSION = 1

# -------- Canale logice --------
CH_CONTROL = "control"
CH_VIDEO = "video"
CH_INPUT = "input"
CH_CLIPBOARD = "clipboard"
CH_FILES = "files"
CH_SYSTEM = "system"
CH_EVENTS = "events"
CHANNELS = {CH_CONTROL, CH_VIDEO, CH_INPUT, CH_CLIPBOARD, CH_FILES, CH_SYSTEM, CH_EVENTS}

# -------- Capabilitati cunoscute (cheile din machines.capabilities) --------
CAP_REMOTE_DESKTOP = "remote_desktop"
CAP_REMOTE_INPUT = "remote_input"
CAP_MULTI_MONITOR = "multi_monitor"
CAP_CLIPBOARD = "clipboard"
CAP_FILE_TRANSFER = "file_transfer"
CAP_SHELL = "shell"
CAP_SYSTEM_INFO = "system_info"
KNOWN_CAPS = [CAP_REMOTE_DESKTOP, CAP_REMOTE_INPUT, CAP_MULTI_MONITOR,
              CAP_CLIPBOARD, CAP_FILE_TRANSFER, CAP_SHELL, CAP_SYSTEM_INFO]

# -------- Platforme cunoscute --------
PLATFORMS = ["windows", "macos", "linux", "android", "ios"]

# -------- Canale de update (per platforma + arhitectura) --------
UPDATE_CHANNELS = ["windows-x64", "windows-arm64", "macos-arm64", "macos-x64",
                   "linux-x64", "linux-arm64", "android", "ios"]


def envelope(ch, t, **fields):
    """Construieste un mesaj de protocol."""
    if ch not in CHANNELS:
        raise ValueError("canal necunoscut: %r" % ch)
    msg = {"ch": ch, "t": t}
    msg.update(fields)
    return msg


def dumps(ch, t, **fields):
    return json.dumps(envelope(ch, t, **fields))


def parse(raw):
    """Returneaza (ch, t, msg) sau (None, None, None) daca e invalid."""
    try:
        m = json.loads(raw)
        if isinstance(m, dict) and m.get("ch") in CHANNELS and "t" in m:
            return m["ch"], m["t"], m
    except Exception:
        pass
    return None, None, None


def normalize_caps(caps):
    """Normalizeaza dict-ul de capabilitati la chei cunoscute (bool)."""
    caps = caps or {}
    return {k: bool(caps.get(k, False)) for k in KNOWN_CAPS}


def default_caps_for(platform):
    """Capabilitati implicite per platforma (folosite daca agentul nu le declara)."""
    base = {k: False for k in KNOWN_CAPS}
    if platform in ("windows", "macos", "linux"):
        base.update({CAP_REMOTE_DESKTOP: True, CAP_REMOTE_INPUT: True,
                     CAP_MULTI_MONITOR: True, CAP_CLIPBOARD: True,
                     CAP_FILE_TRANSFER: True, CAP_SYSTEM_INFO: True})
    elif platform in ("android", "ios"):
        base.update({CAP_REMOTE_DESKTOP: True, CAP_SYSTEM_INFO: True})
    return base
