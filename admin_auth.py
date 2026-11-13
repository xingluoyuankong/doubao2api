"""Admin authentication for the doubao2api console (chat2api-style).

Frontend native login page (not browser Basic Auth pop-up).

Rules:
- Username is fixed ``admin``.
- The password is NEVER stored in plaintext anywhere in this repo.
  Only its SHA-256 hex digest is configured, via the environment variable
  ``DOUBAO2API_ADMIN_PASSWORD_SHA256`` (server .env, 0600, never committed).
  The digest is read at request time, so tests can set it in-process.
- Successful login issues a random 7-day HttpOnly session cookie
  (``doubao2api_admin``), kept only in memory; a restart logs everyone out.
- Failed logins are counted per client IP: 5 consecutive failures lock
  that IP out for 10 minutes. The failure message never says whether the
  username or the password was wrong.
- When no digest is configured, login always fails closed (401): the
  console can never be opened without an admin password having been set.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from typing import Dict, Optional, Tuple

COOKIE_NAME = "doubao2api_admin"
SESSION_TTL_S = 7 * 24 * 3600
MAX_FAILS = 5
LOCK_SECONDS = 600

_sessions: Dict[str, float] = {}          # token -> expiry epoch
_failures: Dict[str, Dict[str, float]] = {}  # ip -> {"fails": n, "locked_until": ts}


def _admin_hash() -> str:
    return os.environ.get("DOUBAO2API_ADMIN_PASSWORD_SHA256", "").strip().lower()


def _client_ip(request) -> str:
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        return xff.split(",")[0].strip()
    real = request.headers.get("X-Real-IP", "")
    if real:
        return real.strip()
    client = getattr(request, "client", None)
    return getattr(client, "host", "unknown") or "unknown"


def _is_locked(ip: str) -> bool:
    rec = _failures.get(ip)
    if not rec:
        return False
    if rec.get("locked_until", 0) > time.time():
        return True
    if rec.get("fails", 0) >= MAX_FAILS:
        # Lock expired: reset the counter so a fresh series can start.
        _failures.pop(ip, None)
    return False


def _record_failure(ip: str) -> None:
    rec = _failures.setdefault(ip, {"fails": 0, "locked_until": 0.0})
    rec["fails"] = rec.get("fails", 0) + 1
    if rec["fails"] >= MAX_FAILS:
        rec["locked_until"] = time.time() + LOCK_SECONDS


def _reset_failures(ip: str) -> None:
    _failures.pop(ip, None)


def check_admin_cookie(request) -> Optional[str]:
    """Return 'admin' when the request carries a live admin session."""
    token = request.cookies.get(COOKIE_NAME, "")
    if not token:
        return None
    expiry = _sessions.get(token)
    if not expiry:
        return None
    if expiry < time.time():
        _sessions.pop(token, None)
        return None
    return "admin"


def attempt_login(request, username: str, password: str) -> Tuple[int, str, Optional[str]]:
    """Try an admin login. Returns (status, message, session_token|None).

    200: ok, token issued. 401: generic failure (never distinguishes
    username vs password, never says whether a digest is configured).
    429: this IP is locked out after 5 failures.
    """
    ip = _client_ip(request)
    if _is_locked(ip):
        return 429, "登录失败次数过多，请 10 分钟后再试", None
    digest = _admin_hash()
    ok = False
    if digest and username == "admin" and isinstance(password, str) and password:
        candidate = hashlib.sha256(password.encode("utf-8")).hexdigest()
        ok = hmac.compare_digest(candidate, digest)
    if not ok:
        _record_failure(ip)
        return 401, "账号或密码错误", None
    _reset_failures(ip)
    token = secrets.token_urlsafe(32)
    _sessions[token] = time.time() + SESSION_TTL_S
    return 200, "登录成功", token


def invalidate_session(request) -> None:
    token = request.cookies.get(COOKIE_NAME, "")
    if token:
        _sessions.pop(token, None)
