"""Integrare pentru serverul v4 (HTTP/WS pe canale, RBAC, enrollment, relay)."""
import asyncio, threading, os, base64, json, time, struct, tempfile, sys
from http.cookiejar import CookieJar
import urllib.request, urllib.error

TMP = tempfile.mkdtemp()
os.environ.update({
    "US_DATA_DIR": TMP, "US_PORT": "8790",
    "US_BOOTSTRAP_ADMIN": "admin", "US_BOOTSTRAP_PASSWORD": "Admin#12345",
    "US_LEGACY_AGENT_KEY": "legacy-key-123", "US_ALLOW_LEGACY_KEY": "1",
})
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from unloadsystem import server as S, db, repositories as repo  # noqa
PORT = 8790
R = []
def check(n, c): R.append((n, bool(c))); print(("  OK  " if c else " FAIL ")+n)

def run():
    loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
    async def go():
        db.init_db()
        srv = await asyncio.start_server(S.handle, "127.0.0.1", PORT)
        async with srv: await srv.serve_forever()
    loop.run_until_complete(go())
threading.Thread(target=run, daemon=True).start()
time.sleep(0.8)

class C:
    def __init__(s, r, w): s.r, s.w = r, w
    async def send_text(s, t): await s._s(0x1, t.encode())
    async def send_bin(s, b): await s._s(0x2, b)
    async def _s(s, op, d):
        n=len(d); h=bytearray([0x80|op]); mk=os.urandom(4)
        if n<126: h.append(0x80|n)
        elif n<65536: h.append(0x80|126); h+=struct.pack("!H",n)
        else: h.append(0x80|127); h+=struct.pack("!Q",n)
        h+=mk; d=bytes(d[i]^mk[i%4] for i in range(n)); s.w.write(bytes(h)+d); await s.w.drain()
    async def recv(s):
        hdr=await s.r.readexactly(2); op=hdr[0]&0x0F; ln=hdr[1]&0x7F
        if ln==126: ln=struct.unpack("!H",await s.r.readexactly(2))[0]
        elif ln==127: ln=struct.unpack("!Q",await s.r.readexactly(8))[0]
        d=await s.r.readexactly(ln) if ln else b""
        return ("text",d.decode()) if op==0x1 else ("binary",d) if op==0x2 else ("close",None)

async def ws_open(path, cookie=None):
    r,w=await asyncio.open_connection("127.0.0.1",PORT)
    k=base64.b64encode(os.urandom(16)).decode()
    req=f"GET {path} HTTP/1.1\r\nHost: x\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {k}\r\nSec-WebSocket-Version: 13\r\n"
    if cookie: req+=f"Cookie: {cookie}\r\n"
    req+="\r\n"; w.write(req.encode()); await w.drain()
    assert b"101" in await r.readline()
    while True:
        h=await r.readline()
        if h in (b"\r\n",b"",b"\n"): break
    return C(r,w)

def opener():
    cj=CookieJar(); return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj)), cj
def login(op, user, pw):
    from urllib.parse import urlencode
    try: op.open(urllib.request.Request(f"http://127.0.0.1:{PORT}/login",
        data=urlencode({"user":user,"password":pw}).encode(), method="POST"), timeout=5)
    except Exception: pass
def cookie_of(cj):
    for c in cj:
        if c.name=="us_sess": return "us_sess="+c.value
    return None
def api(op, path, data=None):
    url=f"http://127.0.0.1:{PORT}{path}"; hdr={}; raw=None
    if data is not None: raw=json.dumps(data).encode(); hdr={"Content-Type":"application/json"}
    try:
        res=op.open(urllib.request.Request(url,data=raw,headers=hdr,method="POST" if data is not None else "GET"),timeout=5)
        return res.status, json.loads(res.read().decode())
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read().decode())
        except Exception: return e.code, {}

CAPS={"remote_desktop":True,"remote_input":True,"multi_monitor":True,"clipboard":True,
      "file_transfer":True,"shell":False,"system_info":True}

async def main():
    # bootstrap admin must_change: login + schimbare parola
    op,cj=opener(); login(op,"admin","Admin#12345")
    check("login admin -> cookie", cookie_of(cj) is not None)
    st,b=api(op,"/change-password",{"old":"Admin#12345","new":"NouaParola#1"})
    check("schimbare parola", b.get("ok"))
    # reconectare cu parola noua
    op,cj=opener(); login(op,"admin","NouaParola#1"); ck=cookie_of(cj)
    check("login cu parola noua", ck is not None)

    st,b=api(op,"/api/machines"); check("machines gol", st==200 and b["machines"]==[])

    # agent (legacy key) + capabilities
    ag=await ws_open("/agent-ws")
    await ag.send_text(json.dumps({"ch":"control","t":"hello","key":"legacy-key-123",
        "device_id":"dev1","platform":"windows","platform_version":"11 23H2","agent_version":"4.0.0",
        "architecture":"x64","hostname":"ACME-PC","name":"PC-01","company":"Acme","capabilities":CAPS}))
    k,d=await ag.recv(); m=json.loads(d); check("agent ok", m.get("t")=="ok" and m.get("device_id")=="dev1")
    k,d=await ag.recv(); check("agent watch off", json.loads(d).get("t")=="watch")
    await asyncio.sleep(0.2)
    st,b=api(op,"/api/machines"); M=b["machines"]
    check("masina online cu capabilities+platform", len(M)==1 and M[0]["online"] and M[0]["platform"]=="windows" and M[0]["capabilities"]["file_transfer"]==True)

    # agent cu cheie gresita -> denied
    bad=await ws_open("/agent-ws")
    await bad.send_text(json.dumps({"ch":"control","t":"hello","key":"gresit","device_id":"x"}))
    k,d=await bad.recv(); check("cheie gresita -> denied", json.loads(d).get("t")=="denied")

    # viewer conecteaza (admin are remote_control)
    vw=await ws_open("/view-ws/dev1", cookie=ck)
    k,d=await vw.recv(); mm=json.loads(d); check("viewer primeste caps", mm.get("ch")=="control" and mm.get("t")=="caps")
    k,d=await ag.recv(); check("agent watch on", json.loads(d).get("t")=="watch" and json.loads(d).get("on")==True)

    # input viewer -> agent (canal input)
    await vw.send_text(json.dumps({"ch":"input","t":"move","x":0.5,"y":0.5}))
    k,d=await ag.recv(); mi=json.loads(d); check("agent primeste input", mi.get("ch")=="input" and mi.get("t")=="move")
    # setmon (system)
    await vw.send_text(json.dumps({"ch":"system","t":"setmon","i":2}))
    k,d=await ag.recv(); check("agent primeste setmon", json.loads(d).get("t")=="setmon")
    # video agent -> viewer (binary)
    await ag.send_bin(b"\xff\xd8VIDEO")
    k,d=await vw.recv(); check("viewer primeste video binar", k=="binary" and d==b"\xff\xd8VIDEO")
    # files viewer -> agent
    await vw.send_text(json.dumps({"ch":"files","t":"up-begin","fid":"f","name":"a.txt"}))
    k,d=await ag.recv(); check("agent primeste up-begin", json.loads(d).get("ch")=="files")
    # files agent -> viewer
    await ag.send_text(json.dumps({"ch":"files","t":"ls-res","path":"C:/","entries":[]}))
    k,d=await vw.recv(); check("viewer primeste ls-res", json.loads(d).get("t")=="ls-res")

    # machine management (admin)
    st,b=api(op,"/api/machines/rename",{"device_id":"dev1","name":"Server","company":"Datasol"})
    check("rename admin ok", b.get("ok"))

    # enrollment token + agent nou cu token
    st,b=api(op,"/api/enroll-tokens/create",{"note":"client X"}); et=b.get("token")
    check("creeaza enroll token", bool(et))
    ag2=await ws_open("/agent-ws")
    await ag2.send_text(json.dumps({"ch":"control","t":"hello","enroll_token":et,"device_id":"dev2",
        "platform":"linux","agent_version":"4.0.0","architecture":"x64","hostname":"srv","name":"Srv-Linux",
        "company":"Acme","capabilities":{"remote_desktop":True,"system_info":True}}))
    k,d=await ag2.recv(); check("agent2 enrolat cu token", json.loads(d).get("t")=="ok")
    # acelasi token refolosit -> denied
    ag3=await ws_open("/agent-ws")
    await ag3.send_text(json.dumps({"ch":"control","t":"hello","enroll_token":et,"device_id":"dev3"}))
    k,d=await ag3.recv(); check("enroll token nu se refoloseste", json.loads(d).get("t")=="denied")

    # ---- RBAC: tehnician ----
    conn=db.connect(); repo.create_user(conn,"teh","TehParola#1",role_name="technician",must_change=False); conn.close()
    opt,cjt=opener(); login(opt,"teh","TehParola#1")
    st,b=api(opt,"/api/machines"); check("tehnician vede masini", st==200)
    st,b=api(opt,"/api/users"); check("tehnician NU vede users (403)", st==403)
    st,b=api(opt,"/api/machines/rename",{"device_id":"dev1","name":"x"}); check("tehnician NU poate rename (403)", st==403)
    st,b=api(opt,"/api/audit"); check("tehnician NU vede audit (403)", st==403)

    # ---- users management ----
    st,b=api(op,"/api/users/add",{"user":"nou","password":"Parola#123","role":"technician"}); check("super_admin adauga user", b.get("ok"))
    st,b=api(op,"/api/users/del",{"user":"admin"}); check("nu te stergi pe tine", st==400)
    st,b=api(op,"/api/users/del",{"user":"nou"}); check("sterge user", b.get("ok"))
    # escaladare: un cont admin (rank 70) NU poate crea super_admin (rank 100)
    conn=db.connect(); repo.create_user(conn,"adm2","AdmParola#1",role_name="admin",must_change=False); conn.close()
    opa,cja=opener(); login(opa,"adm2","AdmParola#1")
    st,b=api(opa,"/api/users/add",{"user":"sup","password":"Parola#123","role":"super_admin"}); check("admin NU creeaza super_admin (403/400)", st in (400,403))
    st,b=api(opa,"/api/users/add",{"user":"teh2","password":"Parola#123","role":"technician"}); check("admin poate crea technician", b.get("ok"))

    # ---- audit populat ----
    st,b=api(op,"/api/audit"); check("audit are intrari", st==200 and len(b["logs"])>0)

    # ---- fara auth ----
    st,b=api(opener()[0],"/api/machines"); check("fara login -> 403", st==403)

asyncio.run(main())
ok=sum(1 for _,c in R if c); tot=len(R)
print(f"\n==== {ok}/{tot} ====")
sys.exit(0 if ok==tot else 1)
