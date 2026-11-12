"""No-account smoke tests for doubao2api-unified skeleton.

Rule: without a Doubao account nothing may report success. These tests
assert the honest failure modes (401 not_logged_in, 503 upstream_not_verified
/ qr_login_unavailable_in_skeleton) and the model catalog shape.
Run:  python -m pytest tests/ -q   (from integrated/)
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DOUBAO_SESSION_FILE", os.path.join(tempfile.gettempdir(), "doubao-unified-test-session.json"))
# Make sure no stray session leaks into the test.
_p = os.environ["DOUBAO_SESSION_FILE"]
if os.path.exists(_p):
    os.remove(_p)

from fastapi.testclient import TestClient  # noqa: E402
from app import app  # noqa: E402
from models import WEB_MODELS, REFERENCE_MODELS  # noqa: E402

client = TestClient(app)


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
    assert len(ids) == len(set(ids)) == 24, ids  # 8 doubao + 16 qianwen
    for must in ["doubao", "doubao-think", "doubao-expert", "doubao-image",
                 "doubao-video", "doubao-music", "qianwen-max", "Qwen3-Coder"]:
        assert must in ids
    assert len(body["reference_models"]) == len(REFERENCE_MODELS)
    assert all(m["web_routable"] is False and m["bot_id"] is None
               for m in body["reference_models"]), "ARK 参考模型绝不能编造 bot_id"


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
