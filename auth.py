"""Session / login handling for doubao2api-unified.

Three login entries, all prepared, none verified without an account:
1. QR scan  -- wang flow (CSRF -> scan_qrcode -> App scan -> sessionid).
   Needs a Playwright browser runtime; the skeleton has no browser, so it
   honestly reports unavailable instead of faking a QR code.
2. Cookie import -- POST /v1/session/cookie {"sessionid": "..."} or the
   DOUBAO_COOKIE env var / .doubao_session.json file (wang session.py order).
3. Session import ("OAuth / logged-in session") -- Doubao has no public
   OAuth client flow usable by a 2api gateway; the feasible path is importing
   an already-logged-in browser session (cookies + device params).

Rules enforced here:
- Storing a session is NOT verification. ``verified`` only becomes True
  after an upstream /chat/completion or /samantha/chat/completion returns 200.
- Credential values are never logged. Session files are written 0600.
- No production credential is used for staging tests; staging must use a
  throwaway session file that is deleted afterwards.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_SESSION_FILE = ".doubao_session.json"


def session_file_path() -> Path:
    return Path(os.environ.get("DOUBAO_SESSION_FILE", DEFAULT_SESSION_FILE))


def load_cookies() -> Dict[str, str]:
    """wang session.py load order: DOUBAO_COOKIE env, then session file."""
    header = os.environ.get("DOUBAO_COOKIE", "").strip()
    if header:
        out: Dict[str, str] = {}
        for item in header.split(";"):
            item = item.strip()
            if not item or "=" not in item:
                continue
            k, v = item.split("=", 1)
            out[k.strip()] = v.strip()
        if out:
            return out
    path = session_file_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    cookies = data.get("cookies", {}) if isinstance(data, dict) else {}
    if not isinstance(cookies, dict):
        return {}
    return {str(k): str(v) for k, v in cookies.items()}


def _read_session_file() -> Dict[str, Any]:
    path = session_file_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def is_verified() -> bool:
    """True only after an upstream /chat/completion returned 200 (see
    mark_verified). A stored session alone never verifies itself."""
    return bool(_read_session_file().get("verified", False))


def session_status() -> Dict[str, Any]:
    cookies = load_cookies()
    return {
        "logged_in": bool(cookies.get("sessionid")),
        "verified": is_verified(),
        "has_sessionid": bool(cookies.get("sessionid")),
        "methods": ["qr-login", "cookie", "session-import", "verify"],
        "session_file": str(session_file_path()),
    }


def store_session(cookies: Dict[str, str], params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Store a session file (0600). Returns status, never the values.

    A newly stored session is always unverified: verification belongs to
    the session's own upstream call, not to the act of storing it.
    """
    if not cookies.get("sessionid"):
        raise ValueError("sessionid is required")
    path = session_file_path()
    data: Dict[str, Any] = {"cookies": cookies, "params": params or {}, "verified": False}
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return {"stored": True, "verified": False,
            "note": "已保存，未验证：只有上游真正返回 200 后 verified 才会变 true。"}


def load_session_params() -> Dict[str, Any]:
    """Device params stored alongside the cookies (device_id/web_id/fp/
    msToken/a_bogus/tea_uuid), or {} when none were imported."""
    params = _read_session_file().get("params", {})
    return dict(params) if isinstance(params, dict) else {}


def mark_verified() -> bool:
    """Mark the stored session verified after an upstream 200.

    Returns False when there is no stored session to mark.
    """
    data = _read_session_file()
    if not data.get("cookies", {}).get("sessionid"):
        return False
    data["verified"] = True
    path = session_file_path()
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return True
