"""doubao2api-unified — FastAPI gateway.

Upstream: Hu410-protocol client (doubao_client.py, POST /chat/completion).
Chat requests are built from the model's routing profile (models.py):
model_item_key is written in three places in the request body
(conversation_init_ext / model_config / aggregate_params) plus
agent_mode / conversation_mode / reasoning_effort.

Without a Doubao account every upstream call still fails loudly (401 when
there is no session, 503 when the session is unverified), never with a
fabricated success. A session becomes verified only after
POST /v1/session/verify gets a real upstream 200. See DESIGN.md.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, AsyncGenerator, Dict

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse

from admin_auth import (COOKIE_NAME, SESSION_TTL_S, attempt_login,
                        check_admin_cookie, invalidate_session)
from auth import (is_verified, load_cookies, load_session_params,
                  mark_verified, session_status, store_session)
from doubao_client import DoubaoClient, UpstreamError, extract_text_from_event
from models import WEB_MODELS, find_model, list_models_payload
from signing_fallback import SigningUnavailable, is_signature_error  # noqa: F401  (fallback contract)

app = FastAPI(title="doubao2api-unified", version="0.2.2-admin-auth")

# In-memory expert-degradation flag (wang ExpertQuotaTracker, skeleton form).
_EXPERT_DEGRADED = False

_STATIC_DIR = Path(__file__).resolve().parent / "static"


def _admin_error(request: Request):
    """401 unless the request carries a live admin session cookie."""
    if check_admin_cookie(request) is None:
        return JSONResponse({"error": {"code": "admin_unauthorized",
                                       "message": "未登录管理员：请先在控制台登录页登录（账号 admin）。"}},
                            status_code=401)
    return None


@app.get("/", include_in_schema=False)
async def console_index(request: Request):
    """Root: console for a logged-in admin, login page otherwise.

    The console used to be open to anyone who opened the domain; it now
    requires the admin login (see admin_auth.py). /health and /v1/models
    stay public: newapi reads the model catalog and health from them.
    """
    if check_admin_cookie(request) is None:
        login = _STATIC_DIR / "login.html"
        if not login.is_file():
            return JSONResponse({"detail": "登录页缺失：static/login.html 不存在"}, status_code=500)
        return FileResponse(str(login), media_type="text/html; charset=utf-8")
    index = _STATIC_DIR / "index.html"
    if not index.is_file():
        return JSONResponse({"detail": "控制台页面缺失：static/index.html 不存在"}, status_code=500)
    return FileResponse(str(index), media_type="text/html; charset=utf-8")


@app.get("/static/login.html", include_in_schema=False)
async def login_page():
    """The login page itself must stay public, or nobody could log in."""
    login = _STATIC_DIR / "login.html"
    if not login.is_file():
        return JSONResponse({"detail": "登录页缺失：static/login.html 不存在"}, status_code=500)
    return FileResponse(str(login), media_type="text/html; charset=utf-8")


@app.get("/static/index.html", include_in_schema=False)
async def console_page(request: Request):
    """The console body is admin-only; unauthenticated requests get 401."""
    err = _admin_error(request)
    if err is not None:
        return err
    index = _STATIC_DIR / "index.html"
    if not index.is_file():
        return JSONResponse({"detail": "控制台页面缺失：static/index.html 不存在"}, status_code=500)
    return FileResponse(str(index), media_type="text/html; charset=utf-8")


@app.get("/auth/status")
async def auth_status(request: Request):
    user = check_admin_cookie(request)
    return {"logged_in": user is not None, "username": user}


@app.post("/auth/login")
async def auth_login(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        body = {}
    status, message, token = attempt_login(
        request, str(body.get("username", "")), str(body.get("password", "")))
    if token is None:
        return JSONResponse({"error": {"code": "login_failed", "message": message}},
                            status_code=status)
    resp = JSONResponse({"logged_in": True, "username": "admin", "message": message})
    resp.set_cookie(COOKIE_NAME, token, max_age=SESSION_TTL_S, httponly=True,
                    samesite="lax", path="/")
    return resp


@app.post("/auth/logout")
async def auth_logout(request: Request):
    invalidate_session(request)
    resp = JSONResponse({"logged_in": False, "message": "已登出"})
    resp.delete_cookie(COOKIE_NAME, path="/")
    return resp


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
    return {"status": "ok" if st["verified"] else "not_ready",
            "logged_in": st["logged_in"], "verified": st["verified"],
            "expert_degraded": _EXPERT_DEGRADED,
            "qianwen_ready": False,
            "models_routable": len(WEB_MODELS),
            "routing_verified_count": sum(1 for m in WEB_MODELS if m.get("verified_routing")),
            "upstream_client": "hu410-chat-completion",
            "skeleton": False,
            "note": "已接 Hu410 协议上游客户端（POST /chat/completion）。verified 仍 false：需账号登录并经 /v1/session/verify 拿到一次真实上游 200；logged_in 只表示本地有 sessionid，不代表上游可用。"}


@app.get("/v1/models")
async def list_models(request: Request):
    err = _auth_error(request)
    if err is not None:
        return err
    return list_models_payload()


@app.get("/admin")
async def admin(request: Request):
    err = _admin_error(request)
    if err is not None:
        return err
    st = session_status()
    return {"service": "doubao2api-unified", "version": "0.2.2-admin-auth",
            "logged_in": st["logged_in"], "verified": st["verified"],
            "models_routable": len(WEB_MODELS),
            "routing_verified_count": sum(1 for m in WEB_MODELS if m.get("verified_routing")),
            "note": "管理页：只返状态，不暴露凭证。verified_routing 全为 false，直到账号实测放行。"}


@app.get("/v1/session/status")
async def session_status_ep(request: Request):
    err = _admin_error(request)
    if err is not None:
        return err
    return session_status()


@app.post("/v1/session/qr-login")
async def qr_login(request: Request):
    err = _admin_error(request)
    if err is not None:
        return err
    # Skeleton: no browser runtime here, so no QR can be honestly produced.
    return JSONResponse(
        {"status": "unavailable_in_skeleton", "code": "qr_login_unavailable_in_skeleton",
         "message": "扫码登录需要部署态的 Playwright 浏览器（wang qr_login.py / BrowserClient 流程：CSRF → scan_qrcode → 豆包 App 扫码）。沙箱骨架无浏览器，不伪造二维码；部署后接通。",
         "next": "部署到 AWS 后，在 /admin 打开扫码页完成登录。"},
        status_code=503)


@app.post("/v1/session/cookie")
async def cookie_login(request: Request, body: Dict[str, Any]):
    err = _admin_error(request)
    if err is not None:
        return err
    sessionid = (body or {}).get("sessionid", "")
    if not isinstance(sessionid, str) or not sessionid.strip():
        return JSONResponse({"error": {"code": "bad_request",
                                       "message": "需要 sessionid 字段"}}, status_code=400)
    try:
        return store_session({"sessionid": sessionid.strip()})
    except ValueError as exc:
        return JSONResponse({"error": {"code": "bad_request", "message": str(exc)}}, status_code=400)


@app.post("/v1/session/import")
async def session_import(request: Request, body: Dict[str, Any]):
    """Import an already-logged-in browser session (cookies + device params).

    This is the feasible 'OAuth / session import' path: Doubao has no public
    OAuth client flow for a 2api gateway, so the import is a session file.
    """
    err = _admin_error(request)
    if err is not None:
        return err
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
    err = _admin_error(request)
    if err is not None:
        return err
    err = _auth_error(request)
    if err is not None:
        return err
    return _upstream_error()


def _resolve_chat_model(body: Dict[str, Any]):
    """Resolve the requested model id to a WEB_MODELS chat entry.

    Returns (entry, None) on success, (None, error_response) on failure.
    Unknown ids and non-chat models (image/music/video/qianwen via this
    endpoint) are rejected with 400 -- before any session check, so the
    caller learns the model is wrong instead of getting a misleading 401.
    """
    model_id = (body or {}).get("model") or "doubao"
    entry = find_model(model_id)
    if entry is None:
        return None, JSONResponse(
            {"error": {"code": "model_not_found",
                       "message": f"未知模型 {model_id}：见 GET /v1/models（共 {len(WEB_MODELS)} 个可路由模型）"}},
            status_code=400)
    if entry.get("kind") != "chat":
        return None, JSONResponse(
            {"error": {"code": "model_not_chat",
                       "message": f"模型 {model_id} 不是聊天模型（kind={entry.get('kind')}），请用对应的生成端点"}},
            status_code=400)
    return entry, None


def _openai_error(code: str, message: str, status: int) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}},
                        status_code=status)


def _openai_response(model_id: str, text: str) -> Dict[str, Any]:
    now = int(time.time())
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
        "object": "chat.completion",
        "created": now,
        "model": model_id,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": text},
                     "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        "note": "usage 为 0：上游 SSE 不返回 token 数，不编造。",
    }


async def _chat_stream_sse(model_id: str, messages: list, profile: Dict[str, Any]):
    """Yield OpenAI-format SSE chunks from the upstream text stream."""
    client = DoubaoClient(load_cookies(), load_session_params())
    chunk_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    created = int(time.time())

    def chunk(content: str, finish: str | None = None) -> str:
        payload = {"id": chunk_id, "object": "chat.completion.chunk", "created": created,
                   "model": model_id,
                   "choices": [{"index": 0,
                                "delta": {"content": content} if content else {},
                                "finish_reason": finish}]}
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    try:
        async for event in client.chat_completion_stream(messages, profile):
            text = extract_text_from_event(event)
            if text and not text.startswith("[错误]"):
                yield chunk(text)
            elif event.get("event") in ("error", "STREAM_ERROR"):
                err = (event.get("data", {}) or {}).get("error_msg", "upstream error")
                yield f"data: {json.dumps({'error': {'code': 'upstream_error', 'message': str(err)}}, ensure_ascii=False)}\n\n"
                return
            if event.get("event") in ("SSE_REPLY_END", "STREAM_END"):
                break
    except UpstreamError as exc:
        yield f"data: {json.dumps({'error': {'code': 'upstream_error', 'message': str(exc)}}, ensure_ascii=False)}\n\n"
        return
    yield chunk("", finish="stop")
    yield "data: [DONE]\n\n"


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    err = _admin_error(request)
    if err is not None:
        return err
    err = _auth_error(request)
    if err is not None:
        return err
    try:
        body = await request.json()
    except Exception:
        return _openai_error("bad_request", "请求体不是合法 JSON", 400)
    if not isinstance(body, dict):
        return _openai_error("bad_request", "请求体必须是 JSON 对象", 400)
    profile, model_err = _resolve_chat_model(body)
    if model_err is not None:
        return model_err
    messages = body.get("messages") or []
    if not isinstance(messages, list) or not any(
            isinstance(m, dict) and m.get("role") == "user" and m.get("content")
            for m in messages):
        return _openai_error("bad_request", "messages 里至少要有一条 user 消息", 400)
    if not load_cookies().get("sessionid"):
        return _upstream_error()  # 401 not_logged_in
    if not is_verified():
        return _upstream_error()  # 503 upstream_not_verified
    model_id = profile["id"]
    try:
        if body.get("stream"):
            return StreamingResponse(
                _chat_stream_sse(model_id, messages, profile),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
        client = DoubaoClient(load_cookies(), load_session_params())
        text = await client.chat_completion(messages, profile)
        return _openai_response(model_id, text)
    except UpstreamError as exc:
        return _openai_error("upstream_error", str(exc), 502)
    except Exception as exc:  # httpx timeouts etc. -- surface, never fake
        return _openai_error("upstream_error", f"上游调用失败：{type(exc).__name__}: {exc}", 502)


@app.post("/v1/session/verify")
async def session_verify(request: Request):
    """Verify the stored session with one minimal real upstream call.

    Sends "hi" to the default fast model (doubao, need_login false) and
    marks the session verified only when upstream returns a real 200 SSE
    reply. No production credential is used here: only the session already
    stored on this deployment. On failure the session stays unverified.
    """
    err = _admin_error(request)
    if err is not None:
        return err
    err = _auth_error(request)
    if err is not None:
        return err
    if not load_cookies().get("sessionid"):
        return _upstream_error()  # 401 not_logged_in
    try:
        body = await request.json()
    except Exception:
        body = {}
    model_id = (body or {}).get("model") or "doubao"
    profile, model_err = _resolve_chat_model({"model": model_id})
    if model_err is not None:
        return model_err
    try:
        client = DoubaoClient(load_cookies(), load_session_params())
        text = await client.chat_completion(
            [{"role": "user", "content": "hi"}], profile, timeout_s=60.0)
    except UpstreamError as exc:
        return _openai_error("upstream_error",
                             f"上游验证失败，会话仍未验证：{exc}", 502)
    except Exception as exc:
        return _openai_error("upstream_error",
                             f"上游验证失败，会话仍未验证：{type(exc).__name__}: {exc}", 502)
    mark_verified()
    return {"verified": True, "model": model_id,
            "reply_preview": text[:200],
            "note": "已验证：上游真实返回 200。此后聊天走上游，不再报 503。"}


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
