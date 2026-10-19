# UnloadSystems Remote — Server (v4, fundație)

Server central cross-platform. **Zero dependințe externe** (doar Python 3.9+ stdlib:
`sqlite3`, `hashlib.scrypt`, WebSocket propriu). Portabil trivial pe Windows/Linux/Docker.

## Design
- **Protocol pe canale** (`control, video, input, clipboard, files, system, events`) — fără mesaje specifice unei platforme.
- **Device capabilities** declarative: fiecare agent declară ce suportă; consola afișează în funcție de ele.
- **Schemă DB platform-agnostică**: un singur tabel `machines` (`platform`, `capabilities` JSON). Fără tabele per-platformă.
- **Securitate**: parole scrypt (swappabil cu Argon2id la deploy), sesiuni cu expirare, enrollment tokens per-dispozitiv, RBAC, audit log. Fără secrete în cod — totul din environment.

## Structură
```
unloadsystem/
  config.py         configurare din env (fara secrete in cod)
  protocol.py       canale + capabilities + envelope mesaje
  security.py       scrypt hash/verify, token-uri
  db.py             sqlite3 + migrations + seed (roluri, bootstrap admin)
  repositories.py   singurul strat care atinge SQL
tests/
  test_foundation.py  37 teste (securitate, DB, repo) — ruleaza cu: python3 tests/test_foundation.py
```

## Configurare (environment)
`US_PORT`, `US_DATA_DIR`, `US_SESSION_TTL`, `US_OFFLINE_AFTER`,
`US_BOOTSTRAP_ADMIN`, `US_BOOTSTRAP_PASSWORD` (gol → parolă random în `data/bootstrap_password.txt`),
`US_LEGACY_AGENT_KEY` + `US_ALLOW_LEGACY_KEY` (tranzitoriu pentru agenții Python v3).

## Status
Fundație (DB + securitate + repositories) completă și testată (37/37).
Următor: handler HTTP/WS pe canale + relay pe această fundație, apoi consola, apoi cut-over de pe serverul stdlib actual.
