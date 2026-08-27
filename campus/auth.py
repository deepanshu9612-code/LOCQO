"""LOCQO authentication — accounts, password hashing, sessions, cookies. Stdlib only.

Roles are `student` and `admin`. A role is ALWAYS a caller argument here and is never
read out of request data — see create_user. Signup in app.py hardcodes "student".
"""
import hashlib
import os
import re
import secrets
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from http.cookies import SimpleCookie

from routing import connect  # shared factory; the foreign-key pragma lives there

COOKIE = "locqo_session"
SESSION_DAYS = 7
# Plain http on localhost can't set Secure, or the cookie is silently dropped.
SECURE_COOKIE = os.environ.get("SECURE_COOKIES") == "1"

_SCRYPT = dict(n=2 ** 14, r=8, p=1, dklen=32)
_DUMMY_SALT = secrets.token_bytes(16)

USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]{3,32}$")
MIN_PASSWORD = 8

# Brute-force throttle, keyed by username+client-ip.
# ponytail: in-memory and per-process — it resets on restart and wouldn't span workers.
#           Move to a table if this ever runs behind more than one process.
MAX_ATTEMPTS = 5
LOCKOUT_SEC = 60
_attempts = {}  # key -> (failure_count, first_failure_monotonic)


def _now():
    return datetime.now(timezone.utc).isoformat()


# ---- passwords -----------------------------------------------------------
def hash_password(password, salt=None):
    """Return (salt_hex, hash_hex). scrypt is memory-hard; stdlib since 3.6."""
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    return salt.hex(), digest.hex()


def verify_password(password, salt_hex, hash_hex):
    _, computed = hash_password(password, bytes.fromhex(salt_hex))
    return secrets.compare_digest(computed, hash_hex)


def _burn():
    """Spend the same work on an unknown username so timing doesn't leak who exists."""
    hashlib.scrypt(b"decoy", salt=_DUMMY_SALT, **_SCRYPT)


# ---- accounts ------------------------------------------------------------
def create_user(con, username, name, password, role="student"):
    """Insert a user. `role` is the CALLER's decision — never pass request data into it."""
    username = (username or "").strip()
    name = (name or "").strip() or username
    if not USERNAME_RE.match(username):
        raise ValueError("Username must be 3–32 characters, using letters, digits, . _ or -")
    if len(password or "") < MIN_PASSWORD:
        raise ValueError(f"Password must be at least {MIN_PASSWORD} characters.")
    if role not in ("student", "admin"):
        raise ValueError("Unknown role.")
    if len(name) > 60:
        raise ValueError("Name is too long.")
    salt, digest = hash_password(password)
    try:
        cur = con.execute(
            "INSERT INTO users (username,name,role,pw_salt,pw_hash,created_at)"
            " VALUES (?,?,?,?,?,?)",
            (username, name, role, salt, digest, _now()),
        )
    except sqlite3.IntegrityError:
        raise ValueError("That username is already taken.")
    return cur.lastrowid


def set_password(con, user_id, password):
    if len(password or "") < MIN_PASSWORD:
        raise ValueError(f"Password must be at least {MIN_PASSWORD} characters.")
    salt, digest = hash_password(password)
    con.execute("UPDATE users SET pw_salt=?, pw_hash=? WHERE id=?", (salt, digest, user_id))
    # every existing session for that account stops working
    con.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))


# ---- login / logout ------------------------------------------------------
def login(con, username, password, client=""):
    """Verify credentials and open a session. Returns (user_row, token)."""
    key = f"{(username or '').lower()}|{client}"
    if _locked(key):
        raise ValueError("Too many failed attempts. Wait a minute and try again.")
    row = con.execute(
        "SELECT * FROM users WHERE username = ? AND active = 1", (username or "",)
    ).fetchone()
    if row is None:
        _burn()
    if row is None or not verify_password(password or "", row["pw_salt"], row["pw_hash"]):
        _record_failure(key)
        raise ValueError("Wrong username or password.")
    _attempts.pop(key, None)
    return row, _open_session(con, row["id"])


def _open_session(con, user_id):
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    con.execute(
        "INSERT INTO sessions (token,user_id,created_at,expires_at) VALUES (?,?,?,?)",
        (token, user_id, now.isoformat(),
         (now + timedelta(days=SESSION_DAYS)).isoformat()),
    )
    return token


def logout(handler):
    token = cookie_token(handler)
    if not token:
        return
    con = connect()
    try:
        con.execute("DELETE FROM sessions WHERE token = ?", (token,))
        con.commit()
    finally:
        con.close()


def current_user(handler):
    """The logged-in user for this request as a dict, or None. Expired sessions are dropped."""
    token = cookie_token(handler)
    if not token:
        return None
    con = connect()
    try:
        row = con.execute(
            "SELECT u.*, s.expires_at FROM sessions s JOIN users u ON u.id = s.user_id"
            " WHERE s.token = ? AND u.active = 1",
            (token,),
        ).fetchone()
        if row is None:
            return None
        if row["expires_at"] <= _now():
            con.execute("DELETE FROM sessions WHERE token = ?", (token,))
            con.commit()
            return None
        return dict(row)
    finally:
        con.close()


def public(user):
    """The only shape of a user that ever reaches the browser — no hash, no salt."""
    return {"username": user["username"], "name": user["name"], "role": user["role"]}


# ---- cookies -------------------------------------------------------------
def cookie_token(handler):
    raw = handler.headers.get("Cookie")
    if not raw:
        return None
    try:
        jar = SimpleCookie(raw)
    except Exception:
        return None
    morsel = jar.get(COOKIE)
    return morsel.value if morsel else None


def cookie_header(token):
    bits = [f"{COOKIE}={token}", "HttpOnly", "SameSite=Strict", "Path=/",
            f"Max-Age={SESSION_DAYS * 86400}"]
    if SECURE_COOKIE:
        bits.append("Secure")
    return "; ".join(bits)


def clear_cookie_header():
    return f"{COOKIE}=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0"


# ---- throttle ------------------------------------------------------------
def _locked(key):
    count, first = _attempts.get(key, (0, 0.0))
    if count < MAX_ATTEMPTS:
        return False
    if time.monotonic() - first < LOCKOUT_SEC:
        return True
    _attempts.pop(key, None)  # window elapsed, start clean
    return False


def _record_failure(key):
    count, first = _attempts.get(key, (0, 0.0))
    if count == 0 or time.monotonic() - first >= LOCKOUT_SEC:
        _attempts[key] = (1, time.monotonic())
    else:
        _attempts[key] = (count + 1, first)
