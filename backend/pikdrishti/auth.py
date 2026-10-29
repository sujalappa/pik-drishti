"""Optional sign-in: user id + password, with an admin who manages the other users.

Sign-in is switched on by setting PIKDRISHTI_ADMIN_PASSWORD (see .env.example). Without it every request is
allowed, as on a local machine. Users added by the admin are stored in <data dir>/users.json, and mirrored to a
private Hugging Face dataset when PIKDRISHTI_USERS_REPO is set, so they survive a restart of a hosted copy.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import threading
import time

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel

from .config import settings

ADMIN_USER = os.environ.get("PIKDRISHTI_ADMIN_USER", "admin").strip() or "admin"
ADMIN_PASSWORD = os.environ.get("PIKDRISHTI_ADMIN_PASSWORD", "")
ENABLED = bool(ADMIN_PASSWORD)
SECRET = (os.environ.get("PIKDRISHTI_SECRET_KEY") or secrets.token_hex(32)).encode()
USERS_REPO = os.environ.get("PIKDRISHTI_USERS_REPO", "").strip()
USERS_TOKEN = os.environ.get("PIKDRISHTI_USERS_TOKEN") or None  # falls back to HF_TOKEN / the saved login
USERS_FILE = "users.json"

TOKEN_TTL_S = 12 * 3600
PBKDF2_ROUNDS = 310_000
USERNAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,31}$")
MIN_PASSWORD = 8
MAX_FAILS, LOCK_S = 5, 300
OPEN_PATHS = ("/api/health", "/api/auth/login", "/api/auth/status")

_lock = threading.Lock()
_users: dict[str, dict] | None = None
_fails: dict[str, tuple[int, float]] = {}


def _hash(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ROUNDS).hex()


_DUMMY_SALT = secrets.token_bytes(16)
_ADMIN_HASH = _hash(ADMIN_PASSWORD, _DUMMY_SALT) if ENABLED else ""


def _path():
    return settings.data_dir / USERS_FILE


def _hub_pull() -> None:
    if not USERS_REPO:
        return
    try:
        from huggingface_hub import hf_hub_download

        src = hf_hub_download(USERS_REPO, USERS_FILE, repo_type="dataset", force_download=True, token=USERS_TOKEN)
        _path().parent.mkdir(parents=True, exist_ok=True)
        _path().write_bytes(open(src, "rb").read())
    except Exception as exc:  # first start (no file yet) or no network: keep the local copy
        print(f"[auth] users not loaded from {USERS_REPO}: {type(exc).__name__}")


def _hub_push() -> None:
    if not USERS_REPO:
        return
    from huggingface_hub import HfApi

    HfApi(token=USERS_TOKEN).upload_file(path_or_fileobj=str(_path()), path_in_repo=USERS_FILE, repo_id=USERS_REPO,
                        repo_type="dataset", commit_message="Update users")


def _load() -> dict[str, dict]:
    global _users
    if _users is None:
        _hub_pull()
        try:
            _users = json.loads(_path().read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError):
            _users = {}
    return _users


def _save() -> None:
    _path().parent.mkdir(parents=True, exist_ok=True)
    tmp = _path().with_suffix(".tmp")
    tmp.write_text(json.dumps(_users, indent=1), encoding="utf-8")
    tmp.replace(_path())
    try:
        _hub_push()
    except Exception as exc:
        raise HTTPException(502, f"Saved on this server, but the permanent copy failed ({type(exc).__name__}). "
                                 "The change will be lost when the server restarts.") from exc


def _role(username: str) -> str | None:
    if username == ADMIN_USER:
        return "admin"
    user = _load().get(username)
    return user["role"] if user else None


def _verify(username: str, password: str) -> bool:
    if username == ADMIN_USER:
        return hmac.compare_digest(_hash(password, _DUMMY_SALT), _ADMIN_HASH)
    user = _load().get(username)
    if user is None:
        _hash(password, _DUMMY_SALT)  # same work as a real check, so unknown ids are not faster
        return False
    return hmac.compare_digest(_hash(password, bytes.fromhex(user["salt"])), user["hash"])


def _token(username: str) -> str:
    body = base64.urlsafe_b64encode(f"{username}|{int(time.time()) + TOKEN_TTL_S}".encode()).decode()
    sig = hmac.new(SECRET, body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def _user_from_token(token: str) -> dict | None:
    try:
        body, sig = token.split(".", 1)
        if not hmac.compare_digest(hmac.new(SECRET, body.encode(), hashlib.sha256).hexdigest(), sig):
            return None
        username, expires = base64.urlsafe_b64decode(body.encode()).decode().rsplit("|", 1)
        if int(expires) < time.time():
            return None
    except (ValueError, UnicodeDecodeError):
        return None
    with _lock:
        role = _role(username)
    return {"username": username, "role": role} if role else None


def _request_user(request: Request) -> dict | None:
    header = request.headers.get("authorization", "")
    token = header[7:] if header.lower().startswith("bearer ") else ""
    if not token and "/files/" in request.url.path:  # images and downloads cannot send a header
        token = request.query_params.get("token", "")
    return _user_from_token(token) if token else None


def require_user(request: Request) -> None:
    """App-wide dependency: every /api route needs a signed-in user once sign-in is switched on."""
    if not ENABLED or request.url.path.endswith(OPEN_PATHS):
        return
    user = _request_user(request)
    if user is None:
        raise HTTPException(401, "Sign in required")
    request.state.user = user


def require_admin(request: Request) -> dict:
    user = getattr(request.state, "user", None)
    if not ENABLED or user is None or user["role"] != "admin":
        raise HTTPException(403, "Only an admin can manage users")
    return user


class Credentials(BaseModel):
    username: str
    password: str


class NewUser(Credentials):
    role: str = "user"


class PasswordChange(BaseModel):
    current: str
    new: str


def status(request: Request) -> dict:
    return {"enabled": ENABLED, "user": _request_user(request) if ENABLED else None}


def login(body: Credentials) -> dict:
    if not ENABLED:
        raise HTTPException(400, "Sign-in is not switched on")
    username = body.username.strip()
    with _lock:
        fails, until = _fails.get(username, (0, 0.0))
        if until > time.time():
            raise HTTPException(429, "Too many wrong attempts. Try again in a few minutes")
        if not _verify(username, body.password):
            fails += 1
            _fails[username] = (0, time.time() + LOCK_S) if fails >= MAX_FAILS else (fails, 0.0)
            raise HTTPException(401, "Wrong user id or password")
        _fails.pop(username, None)
        role = _role(username)
    return {"token": _token(username), "user": {"username": username, "role": role}}


def list_users(_: dict = Depends(require_admin)) -> list[dict]:
    with _lock:
        users = [{"username": name, "role": u["role"], "created_at": u.get("created_at"), "builtin": False}
                 for name, u in sorted(_load().items())]
    return [{"username": ADMIN_USER, "role": "admin", "created_at": None, "builtin": True}] + users


def add_user(body: NewUser, _: dict = Depends(require_admin)) -> dict:
    username = body.username.strip()
    if not USERNAME_RE.fullmatch(username):
        raise HTTPException(400, "User id must be 3–32 letters, digits, dots, dashes or underscores")
    if len(body.password) < MIN_PASSWORD:
        raise HTTPException(400, f"Password must be at least {MIN_PASSWORD} characters")
    if body.role not in ("user", "admin"):
        raise HTTPException(400, "Role must be 'user' or 'admin'")
    with _lock:
        if username == ADMIN_USER or username in _load():
            raise HTTPException(409, "That user id already exists")
        salt = secrets.token_bytes(16)
        _users[username] = {"salt": salt.hex(), "hash": _hash(body.password, salt), "role": body.role,
                            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        _save()
    return {"username": username, "role": body.role}


def remove_user(username: str, admin: dict = Depends(require_admin)) -> dict:
    if username == ADMIN_USER:
        raise HTTPException(400, "The built-in admin cannot be removed")
    if username == admin["username"]:
        raise HTTPException(400, "You cannot remove your own account")
    with _lock:
        if _load().pop(username, None) is None:
            raise HTTPException(404, "User not found")
        _save()
    return {"removed": username}


def change_password(body: PasswordChange, request: Request) -> dict:
    user = getattr(request.state, "user", None)
    if user is None:
        raise HTTPException(401, "Sign in required")
    if user["username"] == ADMIN_USER:
        raise HTTPException(400, "The built-in admin's password is set in the server settings")
    if len(body.new) < MIN_PASSWORD:
        raise HTTPException(400, f"Password must be at least {MIN_PASSWORD} characters")
    with _lock:
        if not _verify(user["username"], body.current):
            raise HTTPException(401, "Current password is wrong")
        salt = secrets.token_bytes(16)
        _users[user["username"]].update(salt=salt.hex(), hash=_hash(body.new, salt))
        _save()
    return {"changed": True}


def register(app: FastAPI) -> None:
    """Add the sign-in routes directly to the app (plain routes, so a host can re-mount them by path)."""
    app.get("/api/auth/status")(status)
    app.post("/api/auth/login")(login)
    app.get("/api/auth/users")(list_users)
    app.post("/api/auth/users")(add_user)
    app.delete("/api/auth/users/{username}")(remove_user)
    app.post("/api/auth/password")(change_password)
