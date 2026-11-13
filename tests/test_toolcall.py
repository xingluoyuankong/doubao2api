"""Tool-call loop tests for doubao2api-unified.

What is being proven here (and what is NOT):

- PROVEN (offline, fake upstream): when a client sends OpenAI `tools`,
  the gateway injects them into the prompt as text, parses the model's
  <tool_call> blocks back into OpenAI `tool_calls` with finish_reason
  "tool_calls", accepts role:tool results on the next request and feeds
  them back to the model (the client-driven loop), caps kept tool rounds
  at DOUBAO_TOOL_MAX_ROUNDS (default 5), and streams tool calls as
  tool_calls deltas. A truncated <tool_call> is auto-continued once.
- NOT PROVEN here: whether the live Doubao upstream actually emits
  <tool_call> blocks for a given model (that needs a logged-in account;
  wang's own live evidence is for its qianwen path + doubao expert).
  Every test below uses a monkeypatched DoubaoClient, never the network.

Run:  python -m pytest tests/test_toolcall.py -q   (from integrated/)
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_smoke import TEST_ADMIN_PASSWORD  # noqa: E402  (reuse the test-only admin password)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app as app_module  # noqa: E402
from app import app  # noqa: E402
from auth import mark_verified, store_session  # noqa: E402
from tool_calling import (  # noqa: E402
    convert_messages_with_tools,
    filter_tool_calls,
    parse_tool_calls_xml,
    strip_tool_call_blocks,
    tool_choice_instruction,
)

TOOLS = [
    {"type": "function", "function": {
        "name": "read_file",
        "description": "Read a file from the filesystem.",
        "parameters": {"type": "object", "properties": {
            "file_path": {"type": "string", "description": "Absolute path"},
            "offset": {"type": "integer", "description": "Line to start from"}},
            "required": ["file_path"]}}},
    {"type": "function", "function": {
        "name": "bash",
        "description": "Execute a shell command.",
        "parameters": {"type": "object", "properties": {
            "command": {"type": "string", "description": "Command to run"}},
            "required": ["command"]}}},
]

CALL_TEXT = (
    '<tool_call>\n'
    '{"name": "read_file", "arguments": {"file_path": "/x.py"}}\n'
    '</tool_call>'
)


def _seed_verified_session():
    # Own stable session file: test_smoke points DOUBAO_SESSION_FILE at a
    # pytest tmp_path that is deleted when its test ends, so writing to
    # that path afterwards raises FileNotFoundError. Point it at a file
    # under the system temp dir that outlives individual tests.
    os.environ["DOUBAO_SESSION_FILE"] = os.path.join(
        tempfile.gettempdir(), "doubao-unified-test-toolcall-session.json")
    store_session({"sessionid": "test-only-session-id"})
    assert mark_verified()


@pytest.fixture()
def client():
    """An admin-logged-in TestClient with a verified (fake) Doubao session.

    Uses a distinct X-Forwarded-For so the admin lockout exercised by
    test_smoke (same test-client IP, 5 failures -> 10 min lock) cannot
    block this login.
    """
    _seed_verified_session()
    c = TestClient(app)
    r = c.post("/auth/login",
               json={"username": "admin", "password": TEST_ADMIN_PASSWORD},
               headers={"X-Forwarded-For": "127.0.0.2"})
    assert r.status_code == 200, r.text
    return c


class FakeClient:
    """Stand-in for DoubaoClient; records prompts, replays canned replies."""

    def __init__(self, script):
        self.script = list(script)
        self.prompts = []
        self.calls = 0

    def _next(self):
        self.calls += 1
        if not self.script:
            return "done"
        return self.script.pop(0)

    async def chat_completion(self, messages, profile, timeout_s=120.0):
        self.prompts.append(messages)
        return self._next()

    async def chat_completion_stream(self, messages, profile, timeout_s=120.0):
        self.prompts.append(messages)
        text = self._next()
        yield {"event": "CHUNK_DELTA", "data": {"text": text}}
        yield {"event": "STREAM_END", "data": {}}


@pytest.fixture()
def fake(monkeypatch):
    holder = {}

    def _install(script):
        fake_client = FakeClient(script)
        holder["client"] = fake_client
        monkeypatch.setattr(app_module, "DoubaoClient",
                            lambda *a, **k: fake_client)
        return fake_client

    return _install


# ── Unit: parser ──

def test_parse_official_two_calls():
    text = ('<tool_call>{"name": "read_file", "arguments": {"file_path": "/a.py"}}</tool_call>\n'
            '<tool_call>{"name": "bash", "arguments": {"command": "ls"}}</tool_call>')
    calls = parse_tool_calls_xml(text)
    assert calls and len(calls) == 2
    assert calls[0]["function"]["name"] == "read_file"
    assert json.loads(calls[0]["function"]["arguments"]) == {"file_path": "/a.py"}
    assert calls[1]["function"]["name"] == "bash"


def test_parse_partial_missing_open_tag():
    # Thinking mode: JSON + closing tag, no opening tag.
    text = '{"name": "read_file", "arguments": {"file_path": "/a.py"}}</tool_call>'
    calls = parse_tool_calls_xml(text)
    assert calls and calls[0]["function"]["name"] == "read_file"


def test_parse_legacy_invoke_format():
    text = ('<tool_calls><invoke name="bash">'
            '<parameter name="command">ls /tmp</parameter>'
            '</invoke></tool_calls>')
    calls = parse_tool_calls_xml(text)
    assert calls and calls[0]["function"]["name"] == "bash"
    assert json.loads(calls[0]["function"]["arguments"]) == {"command": "ls /tmp"}


def test_parse_plain_text_is_none():
    assert parse_tool_calls_xml("just a normal answer, no tools here.") is None
    assert parse_tool_calls_xml("") is None


def test_filter_drops_unknown_tool_names():
    calls = parse_tool_calls_xml(
        '<tool_call>{"name": "read_file", "arguments": {}}</tool_call>'
        '<tool_call>{"name": "rm_rf_root", "arguments": {}}</tool_call>')
    kept = filter_tool_calls(calls, TOOLS)
    assert kept and len(kept) == 1
    assert kept[0]["function"]["name"] == "read_file"


def test_strip_removes_blocks_keeps_text():
    text = "我先读一下文件。\n" + CALL_TEXT + "\n读完了。"
    assert strip_tool_call_blocks(text) == "我先读一下文件。\n\n读完了。"


def test_tool_choice_instruction():
    assert tool_choice_instruction("auto", TOOLS) == ""
    assert tool_choice_instruction(None, TOOLS) == ""
    assert "至少一个工具" in tool_choice_instruction("required", TOOLS)
    assert "read_file" in tool_choice_instruction(
        {"type": "function", "function": {"name": "read_file"}}, TOOLS)
    # Unknown tool in tool_choice must not be forced.
    assert tool_choice_instruction(
        {"type": "function", "function": {"name": "nope"}}, TOOLS) == ""


# ── Unit: prompt conversion + round cap ──

def test_convert_injects_tools_and_tool_result():
    messages = [
        {"role": "system", "content": "You are a coding assistant."},
        {"role": "user", "content": "Fix the bug in auth.py"},
        {"role": "assistant", "content": None,
         "tool_calls": [{"id": "call_1", "type": "function",
                         "function": {"name": "read_file",
                                      "arguments": '{"file_path": "/x.py"}'}}]},
        {"role": "tool", "tool_call_id": "call_1", "name": "read_file",
         "content": "line1: import os\nline2: pass"},
        {"role": "user", "content": "Now fix it"},
    ]
    prompt = convert_messages_with_tools(messages, TOOLS)
    assert "read_file" in prompt and "bash" in prompt
    assert "[工具调用结果]" in prompt
    assert "line1: import os" in prompt
    assert "<tool_call>" in prompt  # assistant call reconstructed for context
    assert "Fix the bug in auth.py" in prompt  # original task preserved


def test_convert_round_cap_keeps_newest_five():
    messages = [{"role": "user", "content": "do the task"}]
    for i in range(7):
        messages.append(
            {"role": "assistant", "content": None,
             "tool_calls": [{"id": f"call_{i}", "type": "function",
                             "function": {"name": "read_file",
                                          "arguments": json.dumps({"file_path": f"/f{i}.py"})}}]})
        messages.append({"role": "tool", "tool_call_id": f"call_{i}",
                         "name": "read_file", "content": f"RESULT-{i}"})
    prompt = convert_messages_with_tools(messages, TOOLS, max_tool_rounds=5)
    assert prompt.count("[工具调用结果]") == 5
    assert "RESULT-0" not in prompt and "RESULT-1" not in prompt
    assert "RESULT-6" in prompt
    assert "earlier tool round(s) omitted" in prompt
    assert "do the task" in prompt


# ── End to end (fake upstream): the client-driven loop ──

def test_e2e_first_round_returns_tool_calls(client, fake):
    fake([CALL_TEXT])
    r = client.post("/v1/chat/completions", json={
        "model": "doubao", "messages": [{"role": "user", "content": "read x.py"}],
        "tools": TOOLS})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["choices"][0]["finish_reason"] == "tool_calls"
    tc = body["choices"][0]["message"]["tool_calls"][0]
    assert tc["function"]["name"] == "read_file"
    assert json.loads(tc["function"]["arguments"]) == {"file_path": "/x.py"}
    # The <tool_call> block itself must not leak into content.
    assert "<tool_call>" not in (body["choices"][0]["message"]["content"] or "")


def test_e2e_loop_round_two_feeds_tool_result_back(client, fake):
    fc = fake(["done, the file has a bug on line 2"])
    r = client.post("/v1/chat/completions", json={
        "model": "doubao",
        "messages": [
            {"role": "user", "content": "read x.py"},
            {"role": "assistant", "content": None,
             "tool_calls": [{"id": "call_abc", "type": "function",
                             "function": {"name": "read_file",
                                          "arguments": '{"file_path": "/x.py"}'}}]},
            {"role": "tool", "tool_call_id": "call_abc", "name": "read_file",
             "content": "line1: import os\nline2: pass"},
            {"role": "user", "content": "Now fix it"},
        ],
        "tools": TOOLS})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["choices"][0]["finish_reason"] == "stop"
    assert "bug on line 2" in body["choices"][0]["message"]["content"]
    # The gateway must have fed the tool result to the model this round.
    sent = fc.prompts[0][0]["content"]
    assert "[工具调用结果]" in sent and "line1: import os" in sent
    assert "read_file" in sent


def test_e2e_parallel_false_keeps_first_call_only(client, fake):
    two = ('<tool_call>{"name": "read_file", "arguments": {"file_path": "/a.py"}}</tool_call>'
           '<tool_call>{"name": "bash", "arguments": {"command": "ls"}}</tool_call>')
    fake([two])
    r = client.post("/v1/chat/completions", json={
        "model": "doubao", "messages": [{"role": "user", "content": "do it"}],
        "tools": TOOLS, "parallel_tool_calls": False})
    assert r.status_code == 200, r.text
    calls = r.json()["choices"][0]["message"]["tool_calls"]
    assert len(calls) == 1 and calls[0]["function"]["name"] == "read_file"


def test_e2e_no_call_parsed_returns_plain_text(client, fake):
    fake(["Here is the answer, no tools needed."])
    r = client.post("/v1/chat/completions", json={
        "model": "doubao", "messages": [{"role": "user", "content": "hi"}],
        "tools": TOOLS})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["choices"][0]["finish_reason"] == "stop"
    assert "no tools needed" in body["choices"][0]["message"]["content"]


def test_e2e_tool_choice_none_ignores_tools(client, fake):
    fc = fake(["plain answer"])
    r = client.post("/v1/chat/completions", json={
        "model": "doubao", "messages": [{"role": "user", "content": "hi"}],
        "tools": TOOLS, "tool_choice": "none"})
    assert r.status_code == 200, r.text
    assert r.json()["choices"][0]["finish_reason"] == "stop"
    # With tool_choice=none the tools must NOT be injected into the prompt.
    assert "可用工具" not in fc.prompts[0][0]["content"]


def test_e2e_truncated_call_is_auto_continued_once(client, fake):
    fake(['<tool_call>\n{"name": "read_file", "arguments": {"file_path": "/a.py"',
          '}}\n</tool_call>'])
    r = client.post("/v1/chat/completions", json={
        "model": "doubao", "messages": [{"role": "user", "content": "read a.py"}],
        "tools": TOOLS})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["choices"][0]["finish_reason"] == "tool_calls"
    assert body["choices"][0]["message"]["tool_calls"][0]["function"]["name"] == "read_file"


def test_e2e_stream_tool_calls(client, fake):
    fake(["我来读一下文件。" + CALL_TEXT])
    r = client.post("/v1/chat/completions", json={
        "model": "doubao", "messages": [{"role": "user", "content": "read x.py"}],
        "tools": TOOLS, "stream": True})
    assert r.status_code == 200, r.text
    assert "tool_calls" in r.text
    assert '"finish_reason": "tool_calls"' in r.text
    assert "read_file" in r.text
    assert "我来读一下文件" in r.text  # text before the call still streams
    assert r.text.rstrip().endswith("data: [DONE]")


def test_e2e_bad_tools_is_400(client):
    r = client.post("/v1/chat/completions", json={
        "model": "doubao", "messages": [{"role": "user", "content": "hi"}],
        "tools": [{"type": "function", "function": {"description": "no name"}}]})
    assert r.status_code == 400, r.text
