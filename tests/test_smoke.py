"""No-account smoke tests for doubao2api-unified.

Rule: without a Doubao account nothing may report success. These tests
assert the honest failure modes (401 not_logged_in, 503 upstream_not_verified
/ qr_login_unavailable_in_skeleton), the model catalog shape, and the
Hu410 request builder (offline: it only builds the request body, it never
touches the network).
Run:  python -m pytest tests/ -q   (from integrated/)
"""
import hashlib
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Admin auth test fixture: the digest below is for a throwaway test-only
# password, never a production credential. Production's digest lives only
# in the server .env (DOUBAO2API_ADMIN_PASSWORD_SHA256).
TEST_ADMIN_PASSWORD = "test-admin-password-20261113"
os.environ["DOUBAO2API_ADMIN_PASSWORD_SHA256"] = hashlib.sha256(
    TEST_ADMIN_PASSWORD.encode("utf-8")).hexdigest()

os.environ.setdefault("DOUBAO_SESSION_FILE", os.path.join(tempfile.gettempdir(), "doubao-unified-test-session.json"))
# Make sure no stray session leaks into the test.
_p = os.environ["DOUBAO_SESSION_FILE"]
if os.path.exists(_p):
    os.remove(_p)

from fastapi.testclient import TestClient  # noqa: E402
from app import app  # noqa: E402
from doubao_client import build_completion_request, extract_text_from_event  # noqa: E402
from models import WEB_MODELS, WORK_MODELS, REFERENCE_MODELS, find_model  # noqa: E402


def admin_client():
    """A fresh TestClient already logged in as admin."""
    c = TestClient(app)
    r = c.post("/auth/login", json={"username": "admin", "password": TEST_ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    return c


def anon_client():
    return TestClient(app)


client = admin_client()

# Work-task model routing, from the public menuConfV2 snapshot
# (sources/doubaowork-client/evidence/model_table_20261113.json).
EXPECTED_WORK_KEYS = {
    "doubao-work-auto": "9",
    "doubao-2.1-lite": "seed-lite-7b",
    "doubao-2.1-pro": "5",
    "deepseek-v4.1-flash": "person-deepseek-v4-1-flash-261017",
    "kimi-k3.1-pro": "person-kimi-k3-1-pro-261111",
    "kimi-k3.1-pro-highspeed": "person-kimi-k3-1-pro-highspeed-261111",
    "kimi-k3": "person-kimi-k3-261111",
    "glm-5.3": "person-glm-5-3-261111",
    "glm-5.3-flash": "person-glm-5-3-flash-261111",
    "deepseek-v4-pro": "person-deepseek-v4-pro-ga-260813",
}
EXPECTED_MULTIPLIERS = {
    "doubao-work-auto": None,
    "doubao-2.1-lite": "0.01x",
    "doubao-2.1-pro": "0.65x",
    "deepseek-v4.1-flash": "0.01x",
    "kimi-k3.1-pro": "0.95x",
    "kimi-k3.1-pro-highspeed": "1.44x",
    "kimi-k3": "1.48x",
    "glm-5.3": "0.80x",
    "glm-5.3-flash": "0.08x",
    "deepseek-v4-pro": None,
}


def test_root_serves_console_not_404():
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "doubao2api 控制台" in r.text
    assert "服务状态" in r.text
    assert "模型列表" in r.text
    assert "登录" in r.text
    assert "聊天测试" in r.text


def test_root_anon_serves_login_page_not_console():
    r = anon_client().get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "请先登录" in r.text
    assert "服务状态" not in r.text
    assert "聊天测试" not in r.text


def test_static_index_served():
    r = client.get("/static/index.html")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "doubao2api 控制台" in r.text


def test_static_index_anon_is_401():
    r = anon_client().get("/static/index.html")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "admin_unauthorized"


def test_static_login_page_is_public():
    r = anon_client().get("/static/login.html")
    assert r.status_code == 200
    assert "请先登录" in r.text


def test_admin_endpoints_anon_are_401():
    anon = anon_client()
    assert anon.get("/admin").status_code == 401
    assert anon.get("/v1/session/status").status_code == 401
    assert anon.post("/v1/session/cookie", json={"sessionid": "x"}).status_code == 401
    assert anon.post("/v1/session/qr-login", json={}).status_code == 401
    assert anon.post("/v1/session/verify", json={}).status_code == 401
    r = anon.post("/v1/chat/completions",
                  json={"model": "doubao", "messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "admin_unauthorized"


def test_health_and_models_stay_public():
    anon = anon_client()
    assert anon.get("/health").status_code == 200
    r = anon.get("/v1/models")
    assert r.status_code == 200
    assert len(r.json()["data"]) == 34


def test_login_wrong_password_is_generic_401():
    anon = anon_client()
    r = anon.post("/auth/login", json={"username": "admin", "password": "wrong"},
                  headers={"X-Forwarded-For": "203.0.113.10"})
    assert r.status_code == 401
    assert r.json()["error"]["message"] == "账号或密码错误"
    r2 = anon.post("/auth/login", json={"username": "not-admin", "password": TEST_ADMIN_PASSWORD},
                   headers={"X-Forwarded-For": "203.0.113.11"})
    assert r2.status_code == 401
    assert r2.json()["error"]["message"] == "账号或密码错误"


def test_login_success_then_logout():
    c = anon_client()
    assert c.get("/auth/status").json() == {"logged_in": False, "username": None}
    r = c.post("/auth/login", json={"username": "admin", "password": TEST_ADMIN_PASSWORD})
    assert r.status_code == 200
    assert r.json()["logged_in"] is True
    assert c.get("/auth/status").json() == {"logged_in": True, "username": "admin"}
    assert "服务状态" in c.get("/").text
    r = c.post("/auth/logout")
    assert r.status_code == 200
    assert c.get("/auth/status").json() == {"logged_in": False, "username": None}
    assert "请先登录" in c.get("/").text


def test_login_lockout_after_five_failures():
    anon = anon_client()
    headers = {"X-Forwarded-For": "203.0.113.99"}
    for _ in range(5):
        r = anon.post("/auth/login", json={"username": "admin", "password": "wrong"},
                      headers=headers)
        assert r.status_code == 401
    r = anon.post("/auth/login", json={"username": "admin", "password": "wrong"},
                  headers=headers)
    assert r.status_code == 429
    # Even the right password is refused while locked.
    r = anon.post("/auth/login", json={"username": "admin", "password": TEST_ADMIN_PASSWORD},
                  headers=headers)
    assert r.status_code == 429


def test_health_not_ready_without_account():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["logged_in"] is False
    assert body["verified"] is False
    assert body["status"] == "not_ready"
    assert body["models_routable"] == len(WEB_MODELS)


def test_models_lists_all_routable_plus_reference():
    r = client.get("/v1/models")
    assert r.status_code == 200
    body = r.json()
    ids = [m["id"] for m in body["data"]]
    assert len(ids) == len(set(ids)) == 34, ids  # 8 doubao + 16 qianwen + 10 work
    for must in ["doubao", "doubao-think", "doubao-expert", "doubao-image",
                 "doubao-video", "doubao-music", "qianwen-max", "Qwen3-Coder"]:
        assert must in ids
    for must in EXPECTED_WORK_KEYS:
        assert must in ids, must
    assert len(body["reference_models"]) == len(REFERENCE_MODELS)
    assert all(m["web_routable"] is False and m["bot_id"] is None
               for m in body["reference_models"]), "ARK 参考模型绝不能编造 bot_id"
    # No model is advertised as verified: routing keys come from a public
    # page, live verification still needs a logged-in account.
    assert body["routing_verified_count"] == 0
    assert all(m["verified_routing"] is False for m in body["data"])


def test_work_models_carry_hu410_routing_profiles():
    assert len(WORK_MODELS) == 10
    for entry in WORK_MODELS:
        assert entry["mode_id"] == "3" and entry["agent_mode"] == 1
        assert entry["conversation_mode"] == 1
        assert entry["bot_id"] == "7338286299411103781"
        assert entry["verified_routing"] is False
        assert entry["model_item_key"] == EXPECTED_WORK_KEYS[entry["id"]]
        assert entry["billing_multiplier"] == EXPECTED_MULTIPLIERS[entry["id"]]
        assert entry["reasoning_effort"] in entry["reasoning_effort_levels"]
        assert entry["model_extra_params"].get("total_window_size")
    # GLM models only offer reasoning levels 3/5/7 (no 4, no 6).
    assert find_model("glm-5.3")["reasoning_effort_levels"] == [3, 5, 7]
    assert find_model("glm-5.3-flash")["reasoning_effort_levels"] == [3, 5, 7]
    # item_id 10001 is shared by every third-party model: it is NOT a key.
    third_party = [m for m in WORK_MODELS if m["model_item_key"].startswith("person-")]
    assert len(third_party) == 7
    assert all(m["item_id"] == 10001 for m in third_party)
    assert len({m["model_item_key"] for m in third_party}) == 7


def test_request_builder_writes_model_item_key_three_times():
    for model_id, key in EXPECTED_WORK_KEYS.items():
        profile = find_model(model_id)
        body = build_completion_request("hi", profile, "local-conv-1")
        opt = body["option"]
        assert opt["conversation_init_ext"]["model_item_key"] == key
        assert opt["model_config"]["model_item_key"] == key
        assert opt["aggregate_params"]["model_item_key"] == key
        assert opt["agent_mode"] == 1
        assert opt["conversation_mode"] == 1
        assert opt["model_config"]["reasoning_effort"] == profile["reasoning_effort"]
        assert opt["model_config"]["model_extra_params"] == profile["model_extra_params"]
        assert body["client_meta"]["bot_id"] == "7338286299411103781"
        # mode_id / provider_id stay empty per the Hu410 capture; inventing
        # values here would be fabrication, not routing.
        assert opt["aggregate_params"]["mode_id"] == ""
        assert opt["aggregate_params"]["provider_id"] == ""
    # Old fast model: key 0, agent_mode 2 (dialogue mode).
    body = build_completion_request("hi", find_model("doubao"), "local-conv-1")
    assert body["option"]["model_config"]["model_item_key"] == "0"
    assert body["option"]["agent_mode"] == 2
    # wang-only model without a key: falls back to need_deep_think, no model_config.
    body = build_completion_request("hi", find_model("doubao-expert"), "local-conv-1")
    assert "model_config" not in body["option"]
    assert body["option"]["need_deep_think"] == 3


def test_sse_text_extraction_offline():
    assert extract_text_from_event(
        {"event": "CHUNK_DELTA", "data": {"text": "hello"}}) == "hello"
    assert extract_text_from_event(
        {"event": "STREAM_MSG_NOTIFY",
         "data": {"content": {"content_block": [
             {"content": {"text_block": {"text": "full snapshot"}}}]}}}) == "full snapshot"
    assert extract_text_from_event({"event": "STREAM_END", "data": {}}) is None


def test_chat_unknown_model_is_400_not_401():
    r = client.post("/v1/chat/completions",
                    json={"model": "no-such-model",
                          "messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "model_not_found"


def test_chat_non_chat_model_is_400():
    r = client.post("/v1/chat/completions",
                    json={"model": "doubao-image",
                          "messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "model_not_chat"


def test_chat_work_model_without_account_is_401():
    r = client.post("/v1/chat/completions",
                    json={"model": "deepseek-v4.1-flash",
                          "messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "not_logged_in"


def test_chat_without_account_is_401_not_fake_success():
    r = client.post("/v1/chat/completions",
                    json={"model": "doubao", "messages": [{"role": "user", "content": "hi"}]})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "not_logged_in"


def test_generations_without_account_are_401():
    for path, payload in [
        ("/v1/images/generations", {"model": "doubao-image", "prompt": "cat"}),
        ("/v1/videos/generations", {"model": "doubao-video", "prompt": "cat"}),
        ("/v1/audio/generations", {"model": "doubao-music", "prompt": "song"}),
        ("/v1/files", {}),
    ]:
        r = client.post(path, json=payload)
        assert r.status_code == 401, (path, r.status_code, r.text)


def test_qr_login_is_honestly_unavailable_in_skeleton():
    r = client.post("/v1/session/qr-login", json={})
    assert r.status_code == 503
    assert r.json()["code"] == "qr_login_unavailable_in_skeleton"


def test_cookie_import_stores_but_does_not_verify():
    with tempfile.TemporaryDirectory() as td:
        os.environ["DOUBAO_SESSION_FILE"] = os.path.join(td, "s.json")
        r = client.post("/v1/session/cookie", json={"sessionid": "test-only-not-real"})
        assert r.status_code == 200
        assert r.json() == {"stored": True, "verified": False,
                            "note": "已保存，未验证：只有上游真正返回 200 后 verified 才会变 true。"}
        # Stored session -> chat must now be 503 upstream_not_verified, never 200.
        r2 = client.post("/v1/chat/completions",
                         json={"model": "doubao", "messages": [{"role": "user", "content": "hi"}]})
        assert r2.status_code == 503
        assert r2.json()["error"]["code"] == "upstream_not_verified"
        # Health still says verified False.
        assert client.get("/health").json()["verified"] is False
        # Session file is 0600 and holds no other secret.
        import stat
        assert stat.S_IMODE(os.stat(os.path.join(td, "s.json")).st_mode) == 0o600
