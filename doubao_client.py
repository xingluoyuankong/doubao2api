"""Doubao web chat upstream client (Hu410 protocol).

Implements POST https://www.doubao.com/chat/completion per Hu410/Doubao2api
(2026-09 capture, pc_version 3.38.5) with the model profiles from
sources/doubaowork-client/evidence/model_table_20261113.json
(unlogged GET https://www.doubao.com/chat, 2026-11-13 00:21 CST,
window._ROUTER_DATA menuConfV2, pc_version 3.45.5).

Routing (deepdive report §2): one bot_id 7338286299411103781 for every
model; the model is selected by `model_item_key`, written in THREE places
in the request body:
  1. option.conversation_init_ext.model_item_key
  2. option.model_config.model_item_key
  3. option.aggregate_params.model_item_key
plus option.agent_mode (2=chat, 1=work task), option.conversation_mode
(1=chat for all models, Hu410 capture), option.model_config.reasoning_effort
and option.model_config.model_extra_params.

Two things Hu410 sends as empty strings and this client keeps empty on
purpose (do NOT invent values; both are pending live verification):
  - option.aggregate_params.mode_id ("" in Hu410; menuConfV2 says mode "3"
    for work-task models, whether the server wants "3" here is unverified)
  - option.aggregate_params.provider_id ("" in Hu410; provider_id appears
    0 times in _ROUTER_DATA and in the web chat bundles)

Limits, stated honestly:
- The SSE reply carries text blocks only (STREAM_MSG_NOTIFY / STREAM_CHUNK /
  CHUNK_DELTA). There is no native tool_calls channel. A coding client that
  needs a native tool-call loop cannot get one from this API; the ceiling is
  text simulation (Magpie's <tool_call> prompt format), not a protocol
  feature of this client.
- Multi-turn history is flattened into one text block (Hu410 behaviour):
  "[用户]... [助手]... [用户]..." with a "[系统指令]..." prefix. True
  multi-turn session state is NOT preserved across requests; each call
  starts a new local conversation (reset_conversation).
- Signing: msToken/a_bogus come from the stored session (cookies/params).
  When the pure-HTTP call fails with a signature/risk-control class error,
  signing_fallback.sign_url_once is tried exactly ONCE (lzA6 frontierSign,
  browser launched lazily and closed afterwards), then the error propagates.
  No retry loop, no account switching.
"""
from __future__ import annotations

import hashlib
import json
import time
import uuid
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

from signing_fallback import SigningUnavailable, is_signature_error, sign_url_once

BASE_URL = "https://www.doubao.com"
CHAT_PATH = "/chat/completion"
BOT_ID = "7338286299411103781"
AID = "497858"
PC_VERSION = "3.45.5"  # public page snapshot 2026-11-13; Hu410 used 3.38.5
VERSION_CODE = "20800"

DEFAULT_HEADERS: Dict[str, str] = {
    "accept": "text/event-stream",
    "accept-language": "zh-CN,zh;q=0.9",
    "agw-js-conv": "str",
    "content-type": "application/json",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/149.0.0.0 Safari/537.36"
    ),
    "origin": BASE_URL,
    "referer": f"{BASE_URL}/chat",
}


def flatten_messages(messages: List[Dict[str, str]]) -> str:
    """Flatten a chat history into the single text block Hu410 sends.

    Only user/assistant turns with content are kept, in order.
    """
    dialog = [m for m in (messages or [])
              if m.get("role") in ("user", "assistant") and m.get("content")]
    if not dialog:
        return ""
    if len(dialog) <= 1:
        content = dialog[-1]["content"]
    else:
        lines = []
        for m in dialog:
            prefix = "用户" if m["role"] == "user" else "助手"
            lines.append(f"{prefix}：{m['content']}")
        if dialog[-1]["role"] == "user":
            lines.append("助手：")
        content = "\n".join(lines)
    return (
        "[系统指令] 这是一个全新的独立对话，请忽略之前的所有对话历史。"
        "只回答当前消息的内容。\n[用户消息]" + content
    )


def build_completion_request(content: str, profile: Dict[str, Any],
                             local_conversation_id: str,
                             conversation_id: str = "",
                             last_section_id: str = "",
                             last_message_index: int = 0) -> Dict[str, Any]:
    """Build the POST /chat/completion body for one model profile.

    `profile` is a WEB_MODELS entry (see models.py). When it carries a
    `model_item_key`, the key is written in all three places; otherwise
    (wang-only models such as doubao-expert / doubao-pro-chat) the request
    falls back to wang's need_deep_think field and carries no model_config.
    """
    key = profile.get("model_item_key")
    local_message_id = str(uuid.uuid4())
    block_id = str(uuid.uuid4())
    option: Dict[str, Any] = {
        "send_message_scene": "",
        "create_time_ms": int(time.time() * 1000),
        "collect_id": "",
        "is_audio": False,
        "answer_with_suggest": False,
        "agent_mode": profile.get("agent_mode", 2),
        "tts_switch": False,
        "need_deep_think": 0,
        "click_clear_context": False,
        "from_suggest": False,
        "is_regen": False,
        "is_replace": False,
        "is_from_click_option": False,
        "is_from_click_softlink": False,
        "disable_sse_cache": False,
        "select_text_action": "",
        "is_select_text": False,
        "resend_for_regen": False,
        "scene_type": 0,
        "unique_key": local_conversation_id,
        "start_seq": 0,
        "need_create_conversation": True,
        "regen_query_id": [],
        "edit_query_id": [],
        "regen_instruction": "",
        "no_replace_for_regen": False,
        "message_from": 0,
        "shared_app_name": "",
        "shared_app_id": "",
        "sse_recv_event_options": {"support_chunk_delta": True},
        "support_lazy_fetch_stream": True,
        "is_ai_playground": False,
        "is_old_user": True,
        "recovery_option": {
            "is_recovery": False,
            "req_create_time_sec": int(time.time()),
            "append_sse_event_scene": 0,
        },
        "message_storage_type": 0,
        "related_deleted_message_ids": {},
        "connector_info_list": [],
        "conversation_mode": profile.get("conversation_mode", 1),
    }
    if key is not None:
        # The three model_item_key writes (Hu410 doubao_client.py:448-651).
        option["conversation_init_ext"] = {"model_item_key": key}
        option["model_config"] = {
            "model_item_key": key,
            "model_extra_params": dict(profile.get("model_extra_params") or {}),
            "reasoning_effort": profile.get("reasoning_effort"),
        }
        option["aggregate_params"] = {
            "conversation_mode": str(profile.get("conversation_mode", 1)),
            "mode_id": "",  # Hu410 sends ""; whether "3" is wanted is UNVERIFIED
            "model_item_key": key,
            "agent_mode": str(profile.get("agent_mode", 2)),
            "reasoning_effort": "",
            "provider_id": "",  # 0 occurrences in _ROUTER_DATA; do not invent
        }
    else:
        # wang-only model: route by need_deep_think, no model_config.
        option["need_deep_think"] = profile.get("deep_think") or 0
    return {
        "client_meta": {
            "local_conversation_id": local_conversation_id,
            "conversation_id": conversation_id,
            "bot_id": str(profile.get("bot_id") or BOT_ID),
            "last_section_id": last_section_id,
            "last_message_index": last_message_index,
            "local_permissions": [],
        },
        "messages": [
            {
                "local_message_id": local_message_id,
                "content_block": [
                    {
                        "block_type": 10000,
                        "content": {
                            "text_block": {
                                "text": content,
                                "icon_url": "",
                                "icon_url_dark": "",
                                "summary": "",
                            },
                            "pc_event_block": "",
                        },
                        "block_id": block_id,
                        "parent_id": "",
                        "meta_info": [],
                        "append_fields": [],
                    }
                ],
                "message_status": 0,
            }
        ],
        "option": option,
        "user_context": [],
        "ext": {"use_deep_think": "0", "collection_id": ""},
    }


def extract_text_from_event(event: Dict[str, Any]) -> Optional[str]:
    """Extract the text delta from one parsed SSE event (Hu410 logic)."""
    event_type = event.get("event", "")
    data = event.get("data", {}) or {}
    if event_type == "STREAM_MSG_NOTIFY":
        for block in (data.get("content", {}) or {}).get("content_block", []):
            text = ((block.get("content", {}) or {}).get("text_block", {}) or {}).get("text", "")
            if text:
                return text
    elif event_type == "STREAM_CHUNK":
        for op in data.get("patch_op", []) or []:
            for block in ((op.get("patch_value", {}) or {}).get("content_block", []) or []):
                if block.get("is_finish"):
                    continue
                text = ((block.get("content", {}) or {}).get("text_block", {}) or {}).get("text", "")
                if text:
                    return text
    elif event_type == "CHUNK_DELTA":
        text = data.get("text", "")
        if text:
            return text
    elif event_type == "STREAM_ERROR":
        return f"[错误] {data.get('error_msg', data.get('message', 'Unknown stream error'))}"
    return None


def parse_sse_event(event_str: str) -> Optional[Dict[str, Any]]:
    """Parse one SSE frame (``event: / id: / data:``) into a dict."""
    event_type = ""
    event_id = ""
    data = ""
    for line in event_str.strip().split("\n"):
        if line.startswith("event:"):
            event_type = line[6:].strip()
        elif line.startswith("id:"):
            event_id = line[3:].strip()
        elif line.startswith("data:"):
            data = line[5:].strip()
    if not event_type:
        return None
    try:
        data_obj = json.loads(data) if data else {}
    except (json.JSONDecodeError, ValueError):
        data_obj = {"raw": data}
    return {"event": event_type, "id": event_id, "data": data_obj}


class UpstreamError(RuntimeError):
    """Upstream returned an error (HTTP or business code)."""

    def __init__(self, message: str, code: Any = None):
        super().__init__(message)
        self.code = code


class DoubaoClient:
    """httpx client for POST /chat/completion (Hu410 protocol)."""

    def __init__(self, cookies: Dict[str, str], params: Optional[Dict[str, Any]] = None):
        self.cookies = dict(cookies or {})
        self.params = dict(params or {})
        self.conversation_id = ""
        self.local_conversation_id = ""
        self.last_section_id = ""
        self.last_message_index = 0
        self.web_id = (self.cookies.get("web_id") or self.params.get("web_id")
                       or self._stable_device_id())
        # Frontend device_id takes ttWidConfig.web_id (stable); derive from
        # the session when missing so the fingerprint does not change per call.
        self.device_id = (self.cookies.get("device_id") or self.params.get("device_id")
                          or self.web_id)
        self.tea_uuid = (self.cookies.get("tea_uuid") or self.params.get("tea_uuid")
                         or self.web_id)
        self.fp = self.cookies.get("s_v_web_id", "") or self.params.get("fp", "")
        self.ms_token = self.cookies.get("msToken", "") or self.params.get("msToken", "")
        self.a_bogus = self.cookies.get("a_bogus", "") or self.params.get("a_bogus", "")
        self.bot_id = BOT_ID

    def _stable_device_id(self) -> str:
        seed = (self.cookies.get("sessionid") or self.cookies.get("ttwid")
                or "doubao2api")
        digest = hashlib.md5(seed.encode()).hexdigest()
        return str(10 ** 17 + int(digest[:16], 16) % (9 * 10 ** 16))

    def _query_params(self) -> Dict[str, str]:
        params: Dict[str, str] = {
            "aid": AID,
            "device_id": self.device_id,
            "device_platform": "web",
            "fp": self.fp,
            "language": "zh",
            "pc_version": PC_VERSION,
            "pkg_type": "release_version",
            "real_aid": AID,
            "region": "CN",
            "scene": "chatsse",
            "samantha_web": "1",
            "sys_region": "CN",
            "tea_uuid": self.tea_uuid,
            "use-olympus-account": "1",
            "version_code": VERSION_CODE,
            "web_id": self.web_id,
            "web_platform": "browser",
            "web_tab_id": str(uuid.uuid4()),
        }
        if self.ms_token:
            params["msToken"] = self.ms_token
        if self.a_bogus:
            params["a_bogus"] = self.a_bogus
        params["tz_name"] = "Asia/Shanghai"
        return params

    def _headers(self) -> Dict[str, str]:
        return dict(DEFAULT_HEADERS)

    def reset_conversation(self) -> None:
        self.local_conversation_id = str(uuid.uuid4())
        self.conversation_id = ""
        self.last_section_id = ""
        self.last_message_index = 0

    def _update_state(self, event: Dict[str, Any]) -> None:
        data = event.get("data", {}) or {}
        if event.get("event") == "SSE_ACK":
            meta = data.get("ack_client_meta", {}) or {}
            if meta.get("conversation_id"):
                self.conversation_id = meta["conversation_id"]
            if meta.get("section_id"):
                self.last_section_id = meta["section_id"]
        elif event.get("event") == "STREAM_MSG_NOTIFY":
            meta = data.get("meta", {}) or {}
            if meta.get("index_in_conv"):
                self.last_message_index = meta["index_in_conv"]
            if meta.get("section_id"):
                self.last_section_id = meta["section_id"]
            if meta.get("conversation_id"):
                self.conversation_id = meta["conversation_id"]

    async def _stream_once(self, body: Dict[str, Any], params: Dict[str, str],
                           timeout_s: float):
        """Yield parsed SSE events for one POST; raises UpstreamError."""
        url = f"{BASE_URL}{CHAT_PATH}"
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            async with client.stream("POST", url, params=params,
                                     headers=self._headers(),
                                     cookies=self.cookies, json=body) as resp:
                if resp.status_code != 200:
                    text = ""
                    async for chunk in resp.aiter_text():
                        text += chunk
                    raise UpstreamError(f"HTTP {resp.status_code}: {text[:200]}",
                                        code=resp.status_code)
                content_type = resp.headers.get("content-type", "")
                if "text/event-stream" not in content_type:
                    raw = ""
                    async for chunk in resp.aiter_text():
                        raw += chunk
                    code, msg = 0, raw[:300]
                    try:
                        obj = json.loads(raw)
                        code = obj.get("code", 0)
                        msg = obj.get("msg") or obj.get("message") or raw[:300]
                    except (json.JSONDecodeError, ValueError):
                        pass
                    raise UpstreamError(f"豆包 API 错误 {code}: {msg}", code=code)
                buffer = ""
                async for chunk in resp.aiter_text():
                    buffer += chunk
                    while "\n\n" in buffer:
                        frame, buffer = buffer.split("\n\n", 1)
                        event = parse_sse_event(frame)
                        if event:
                            self._update_state(event)
                            yield event
                if buffer.strip():
                    event = parse_sse_event(buffer)
                    if event:
                        self._update_state(event)
                        yield event

    async def chat_completion_stream(
            self, messages: List[Dict[str, str]], profile: Dict[str, Any],
            timeout_s: float = 120.0) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream parsed SSE events for one chat call.

        On a signature/risk-control class failure, the lzA6 signing
        fallback (single frontierSign attempt) runs once and the request is
        re-sent once; a second failure propagates.
        """
        content = flatten_messages(messages)
        if not content:
            yield {"event": "error", "data": {"error_msg": "No user message found"}}
            return
        self.reset_conversation()
        body = build_completion_request(content, profile, self.local_conversation_id)
        params = self._query_params()
        try:
            async for event in self._stream_once(body, params, timeout_s):
                yield event
            return
        except UpstreamError as exc:
            if not is_signature_error(str(exc)):
                raise
            # Single signing-fallback attempt (DESIGN.md §6).
            fingerprint = {
                "device_id": self.device_id,
                "web_id": self.web_id,
                "tea_uuid": self.tea_uuid,
            }
            if self.fp:
                fingerprint["fp"] = self.fp
            try:
                signed_url = await sign_url_once(
                    f"{BASE_URL}{CHAT_PATH}", params, fingerprint, self.ms_token or None)
            except SigningUnavailable as sign_exc:
                raise UpstreamError(f"签名兜底不可用：{sign_exc}；原错误：{exc}",
                                    code=getattr(exc, "code", None)) from sign_exc
            # sign_url_once returns the full signed URL; re-send with it.
            signed_params = dict(params)
            if "a_bogus=" in signed_url:
                signed_params["a_bogus"] = signed_url.split("a_bogus=", 1)[1].split("&")[0]
            async for event in self._stream_once(body, signed_params, timeout_s):
                yield event

    async def chat_completion(self, messages: List[Dict[str, str]],
                              profile: Dict[str, Any],
                              timeout_s: float = 120.0) -> str:
        """Non-streaming chat: collect all SSE text into one string."""
        full_text = ""
        emitted = ""
        async for event in self.chat_completion_stream(messages, profile, timeout_s):
            etype = event.get("event", "")
            data = event.get("data", {}) or {}
            if etype in ("STREAM_MSG_NOTIFY", "STREAM_CHUNK", "CHUNK_DELTA"):
                text = extract_text_from_event(event)
                if not text:
                    continue
                if etype == "STREAM_MSG_NOTIFY":
                    new_full = text  # full snapshot: replace
                else:
                    new_full = emitted + text
                emitted = new_full
                full_text = emitted
            elif etype in ("SSE_REPLY_END", "STREAM_END"):
                break
            elif etype in ("error", "STREAM_ERROR"):
                raise UpstreamError(data.get("error_msg", "Unknown error"),
                                    code=data.get("error_code"))
        return full_text
