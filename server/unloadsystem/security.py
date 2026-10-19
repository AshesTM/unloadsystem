"""
Securitate: hashing parole (scrypt, stdlib, memory-hard), token-uri sigure.
Nota: pe tintele de deploy cu internet se poate inlocui scrypt cu Argon2id
(interfata verify/hash ramane aceeasi). Aici folosim stdlib ca sa fie
zero-dependinte si testabil oriunde.
"""
import hashlib
import hmac
import os
import secrets

# Parametri scrypt (memory-hard). N=2**14 ~ 16MB, cost rezonabil pe server.
_SCRYPT_N = 2 ** 14
_SCRYPT_R = 8
_SCRYPT_P = 1
_DKLEN = 32
_MAXMEM = 128 * 1024 * 1024  # plafon generos, portabil intre OpenSSL-uri


def hash_password(password):
    """Returneaza un string 'scrypt$N$r$p$salthex$hashhex'."""
    salt = os.urandom(16)
    dk = hashlib.scrypt(password.encode("utf-8"), salt=salt,
                        n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=_DKLEN, maxmem=_MAXMEM)
    return "scrypt$%d$%d$%d$%s$%s" % (_SCRYPT_N, _SCRYPT_R, _SCRYPT_P,
                                      salt.hex(), dk.hex())


def verify_password(password, stored):
    """Verifica in timp constant. Acepta formatul de mai sus."""
    try:
        algo, n, r, p, salt_hex, hash_hex = stored.split("$")
        if algo != "scrypt":
            return False
        dk = hashlib.scrypt(password.encode("utf-8"), salt=bytes.fromhex(salt_hex),
                            n=int(n), r=int(r), p=int(p), dklen=len(hash_hex) // 2,
                            maxmem=_MAXMEM)
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False


def new_token(nbytes=32):
    return secrets.token_urlsafe(nbytes)


def new_device_id():
    return secrets.token_hex(16)


def constant_eq(a, b):
    return hmac.compare_digest(str(a), str(b))
