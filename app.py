"""doubao2api-unified — skeleton FastAPI gateway.

Status: local skeleton only. No upstream client is wired yet on purpose:
without a Doubao account every upstream call must fail loudly (401 when
there is no session, 503 when the session is unverified), never with a
fabricated success. See integrated/DESIGN.md.
"""
from __future__ import annotations

import os
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from auth import load_cookies, session_status, store_session
from models import WEB_MODELS, list_models_payload
from signing_fallback import SigningUnavailable, is_signature_error  # noqa: F401  (fallback contract)

app = FastAPI(title="doubao2api-unified", version="0.1.0-skeleton")

# In-memory expert-degradation flag (wang ExpertQuotaTracker, skeleton form).
_EXPERT_DEGRADED = False


def _require_api_key(request: Request) -> bool:
    expected = os.environ.get("DOUBAO_API_KEY", "")
    if not expected:
        return True  # wang behaviour: empty key means no auth (deployment MUST set one)
    auth = request.headers.get("Authorization", "")
    return auth == f"Bearer {expected}"


def _auth_error(request: Request):
    if not _require_api_key(request):
        return JSONResponse({"error": {"code": "unauthorized",
                                       "message": "Authorization Bearer 与 DOUBAO_API_KEY 不一致"}},
                            status_code=401)
    return None


def _upstream_error():
    cookies = load_cookies()
    if not cookies.get("sessionid"):
        return JSONResponse(
            {"error": {"code": "not_logged_in",
                       "message": "未登录：没有 sessionid。请用 /v1/session/qr-login 扫码、/v1/session/cookie 导入 Cookie、或 /v1/session/import 导入已登录会话。"}},
            status_code=401)
    return JSONResponse(
        {"error": {"code": "upstream_not_verified",
                   "message": "会话已保存但未验证：上游未返回过 200。等主人提供账号并完成一次真实上游调用后才可聊天/生图。"}},
        status_code=503)


@app.get("/health")
async def health() -> Dict[str, Any]:
    st = session_status()
    return {"status": "ok" if st["logged_in"] else "not_ready",
            "logged_in": st["logged_in"], "verified": False,
            "expert_degraded": _EXPERT_DEGRADED,
            "qianwen_ready": False,
            "models_routable": len(WEB_MODELS),
            "skeleton": True,
            "note": "骨架：未接上游。logged_in 只表示本地有 sessionid，不代表上游可用。"}


@app.get("/v1/models")
async def list_models(request: Request):
    err = _auth_error(request)
    if err is not None:
        return err
    return list_models_payload()


@app.get("/admin")
async def admin():
    st = session_status()
    return {"service": "doubao2api-unified", "version": "0.1.0-skeleton",
            "logged_in": st["logged_in"], "verified": False,
            "models_routable": len(WEB_MODELS),
            "note": "骨架管理页：只返状态，不暴露凭证。"}


@app.get("/v1/session/status")
async def session_status_ep():
    return session_status()


@app.post("/v1/session/qr-login")
async def qr_login():
    # Skeleton: no browser runtime here, so no QR can be honestly produced.
    return JSONResponse(
        {"status": "unavailable_in_skeleton", "code": "qr_login_unavailable_in_skeleton",
         "message": "扫码登录需要部署态的 Playwright 浏览器（wang qr_login.py / BrowserClient 流程：CSRF → scan_qrcode → 豆包 App 扫码）。沙箱骨架无浏览器，不伪造二维码；部署后接通。",
         "next": "部署到 AWS 后，在 /admin 打开扫码页完成登录。"},
        status_code=503)


@app.post("/v1/session/cookie")
async def cookie_login(body: Dict[str, Any]):
    sessionid = (body or {}).get("sessionid", "")
    if not isinstance(sessionid, str) or not sessionid.strip():
        return JSONResponse({"error": {"code": "bad_request",
                                       "message": "需要 sessionid 字段"}}, status_code=400)
    try:
        return store_session({"sessionid": sessionid.strip()})
    except ValueError as exc:
        return JSONResponse({"error": {"code": "bad_request", "message": str(exc)}}, status_code=400)


@app.post("/v1/session/import")
async def session_import(body: Dict[str, Any]):
    """Import an already-logged-in browser session (cookies + device params).

    This is the feasible 'OAuth / session import' path: Doubao has no public
    OAuth client flow for a 2api gateway, so the import is a session file.
    """
    cookies = (body or {}).get("cookies", {})
    params = (body or {}).get("params", {})
    if not isinstance(cookies, dict) or not cookies.get("sessionid"):
        return JSONResponse({"error": {"code": "bad_request",
                                       "message": "需要 cookies.sessionid"}}, status_code=400)
    try:
        return store_session({str(k): str(v) for k, v in cookies.items()},
                             {str(k): str(v) for k, v in params.items()} if isinstance(params, dict) else {})
    except ValueError as exc:
        return JSONResponse({"error": {"code": "bad_request", "message": str(exc)}}, status_code=400)


def _upstream_stub(request: Request):
    err = _auth_error(request)
    if err is not None:
        return err
    return _upstream_error()


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    return _upstream_stub(request)


@app.post("/v1/images/generations")
async def images_generations(request: Request):
    return _upstream_stub(request)


@app.post("/v1/images/edits")
async def images_edits(request: Request):
    return _upstream_stub(request)


@app.post("/v1/videos/generations")
async def videos_generations(request: Request):
    return _upstream_stub(request)


@app.post("/v1/audio/generations")
async def audio_generations(request: Request):
    return _upstream_stub(request)


@app.post("/v1/files")
async def files_upload(request: Request):
    return _upstream_stub(request)


@app.get("/v1/files/download")
async def files_download(request: Request):
    return _upstream_stub(request)


@app.post("/v1/images/upload")
async def images_upload(request: Request):
    return _upstream_stub(request)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.environ.get("DOUBAO_HOST", "127.0.0.1"),
                port=int(os.environ.get("DOUBAO_PORT", "8793")))
