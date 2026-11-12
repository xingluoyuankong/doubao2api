"""Full model catalog for doubao2api-unified.

Sources (see reports/models-20261112.md for the full table):
- WANG: sources/wang/doubao2api/unified_server.py CHAT_MODELS / ALL_MODELS,
  sources/wang/doubao2api/qianwen_client.py QIANWEN_MODELS,
  sources/wang/README.md Bot ID / seed_intention / ARK reference table.
- LZA6: sources/lza6/app/core/config.py MODEL_MAPPING (single model).
- ARK: Volcengine Ark public model list / pricing pages, fetched 2026-11-12
  (web search). ARK model IDs are NOT doubao.com web bot_ids and are NOT
  routable through the web reverse-proxy; they are listed under
  REFERENCE_MODELS with web_routable=False. No bot_id is invented here:
  where the web bot_id is unknown it is None.
"""
from __future__ import annotations

# Web-routable through the doubao.com reverse proxy (verified in repo code).
WEB_MODELS = [
    # --- Doubao web modes (wang CHAT_MODELS; need_deep_think 0/1/3) ---
    {"id": "doubao", "owned_by": "doubao", "kind": "chat", "deep_think": 0,
     "bot_id": "7338286299411103781", "source": "wang:unified_server/CHAT_MODELS",
     "note": "快速模式。旧纯HTTP client.py 的 DEFAULT_BOT_ID 是另一值 7234781073513644036，待账号实测钉死。"},
    {"id": "doubao-pro", "owned_by": "doubao", "kind": "chat", "deep_think": 0,
     "bot_id": "7338286299411103781", "source": "wang:unified_server/CHAT_MODELS",
     "note": "doubao 的别名，同为 need_deep_think=0。"},
    {"id": "doubao-think", "owned_by": "doubao", "kind": "chat", "deep_think": 1,
     "bot_id": "7338286299411103781", "source": "wang:unified_server/CHAT_MODELS",
     "note": "思考模式，带思维链 reasoning_content（block_type 10040+10000）。"},
    {"id": "doubao-expert", "owned_by": "doubao", "kind": "chat", "deep_think": 3,
     "bot_id": "7338286299411103781", "source": "wang:unified_server/CHAT_MODELS",
     "note": "专家模式 use_auto_cot；额度耗尽自动降级到 doubao-think（ExpertQuotaTracker）。"},
    {"id": "doubao-pro-chat", "owned_by": "doubao", "kind": "chat", "deep_think": 0,
     "bot_id": "7338286299411103781", "source": "lza6:config/MODEL_MAPPING",
     "note": "lzA6 唯一模型名，映射同一 Bot ID；整合版作 doubao-pro 的别名。"},
    # --- Generation (wang ALL_MODELS) ---
    {"id": "doubao-image", "owned_by": "doubao", "kind": "image", "deep_think": None,
     "bot_id": "7338286299411103781", "source": "wang:unified_server/ALL_MODELS",
     "note": "文生图/图生图，走 /samantha/chat/completion content_type=2009 系。"},
    {"id": "doubao-music", "owned_by": "doubao", "kind": "audio", "deep_think": None,
     "bot_id": "7338286299411103781", "source": "wang:unified_server/ALL_MODELS",
     "note": "文生音乐，走 /samantha/chat/completion content_type=2005。"},
    {"id": "doubao-video", "owned_by": "doubao", "kind": "video", "deep_think": None,
     "bot_id": "7338286299411103781", "source": "wang:unified_server/ALL_MODELS",
     "note": "文生/图生视频，Seedance 2.0 异步两步；每日额度按账号计，待实测。"},
    # --- Qianwen / Qwen (wang qianwen_client.py QIANWEN_MODELS; Playwright browser) ---
    {"id": "qianwen", "owned_by": "qianwen", "kind": "chat", "deep_think": None,
     "bot_id": None, "source": "wang:qianwen_client/QIANWEN_MODELS",
     "note": "映射 Qwen，deep_search=0。走 qianwen.com，非 doubao.com。"},
    {"id": "qianwen-max", "owned_by": "qianwen", "kind": "chat", "deep_think": None,
     "bot_id": None, "source": "wang:qianwen_client/QIANWEN_MODELS",
     "note": "映射 Qwen3.7-Max，deep_search=0。"},
    {"id": "qianwen-max-think", "owned_by": "qianwen", "kind": "chat", "deep_think": None,
     "bot_id": None, "source": "wang:qianwen_client/QIANWEN_MODELS",
     "note": "映射 Qwen3.7-Max，deep_search=1。"},
    {"id": "qianwen-think", "owned_by": "qianwen", "kind": "chat", "deep_think": None,
     "bot_id": None, "source": "wang:qianwen_client/QIANWEN_MODELS",
     "note": "映射 Qwen3-Max-Thinking-Preview。"},
    {"id": "qianwen-coder", "owned_by": "qianwen", "kind": "chat", "deep_think": None,
     "bot_id": None, "source": "wang:qianwen_client/QIANWEN_MODELS",
     "note": "映射 Qwen3-Coder。"},
    {"id": "qianwen-flash", "owned_by": "qianwen", "kind": "chat", "deep_think": None,
     "bot_id": None, "source": "wang:qianwen_client/QIANWEN_MODELS",
     "note": "映射 Qwen3.5-Flash。"},
    {"id": "qianwen-search", "owned_by": "qianwen", "kind": "chat", "deep_think": None,
     "bot_id": None, "source": "wang:qianwen_client/QIANWEN_MODELS",
     "note": "映射 Qwen3.7-Max，deep_search=1（联网搜索）。"},
    {"id": "Qwen", "owned_by": "qianwen", "kind": "chat", "deep_think": None,
     "bot_id": None, "source": "wang:qianwen_client/QIANWEN_MODELS",
     "note": "直通模型码。"},
    {"id": "Qwen3.7-Max", "owned_by": "qianwen", "kind": "chat", "deep_think": None,
     "bot_id": None, "source": "wang:qianwen_client/QIANWEN_MODELS", "note": "直通模型码。"},
    {"id": "Qwen3.5-Plus", "owned_by": "qianwen", "kind": "chat", "deep_think": None,
     "bot_id": None, "source": "wang:qianwen_client/QIANWEN_MODELS", "note": "直通模型码。"},
    {"id": "Qwen3.5-Flash", "owned_by": "qianwen", "kind": "chat", "deep_think": None,
     "bot_id": None, "source": "wang:qianwen_client/QIANWEN_MODELS", "note": "直通模型码。"},
    {"id": "Qwen3-Max", "owned_by": "qianwen", "kind": "chat", "deep_think": None,
     "bot_id": None, "source": "wang:qianwen_client/QIANWEN_MODELS", "note": "直通模型码。"},
    {"id": "Qwen3-Max-Thinking-Preview", "owned_by": "qianwen", "kind": "chat", "deep_think": None,
     "bot_id": None, "source": "wang:qianwen_client/QIANWEN_MODELS", "note": "直通模型码。"},
    {"id": "Qwen3-Coder", "owned_by": "qianwen", "kind": "chat", "deep_think": None,
     "bot_id": None, "source": "wang:qianwen_client/QIANWEN_MODELS", "note": "直通模型码。"},
    {"id": "Qwen3-Coder-Flash", "owned_by": "qianwen", "kind": "chat", "deep_think": None,
     "bot_id": None, "source": "wang:qianwen_client/QIANWEN_MODELS", "note": "直通模型码。"},
    {"id": "Qwen3-235B-A22B-2507", "owned_by": "qianwen", "kind": "chat", "deep_think": None,
     "bot_id": None, "source": "wang:qianwen_client/QIANWEN_MODELS", "note": "直通模型码。"},
]

# ARK / official reference only. NOT routable via the doubao.com web proxy.
# bot_id is deliberately None: the web bot_id for these ARK SKUs is unverified.
REFERENCE_MODELS = [
    {"id": "doubao-seed-2.1-pro", "ark_id": "doubao-seed-2-1-pro-260628", "owned_by": "volcengine",
     "kind": "chat", "context": "256K/1M(0915刷新)", "source": "ark:volcengine 2026-06-23发布",
     "note": "Seed 2.1 旗舰，Coding/Agent/多模态。0915 刷新版 ark_id doubao-seed-2-1-pro-260915。"},
    {"id": "doubao-seed-2.1-turbo", "ark_id": "doubao-seed-2-1-turbo-260628", "owned_by": "volcengine",
     "kind": "chat", "context": "256K", "source": "ark:volcengine 2026-06-23发布",
     "note": "Seed 2.1 性价比档。"},
    {"id": "doubao-seed-2.1-lite", "ark_id": "doubao-seed-2-1-lite-260915", "owned_by": "volcengine",
     "kind": "chat", "context": "1M", "source": "ark:volcengine 2026-09发布",
     "note": "Seed 2.1 轻量，全模态理解，1M 上下文。"},
    {"id": "doubao-seed-evolving", "ark_id": "doubao-seed-evolving", "owned_by": "volcengine",
     "kind": "chat", "context": "up to 1M", "source": "ark:volcengine",
     "note": "周级迭代的滚动模型，单 ID 持续更新，无固定版本号。"},
    {"id": "doubao-seed-2.0-pro", "ark_id": "doubao-seed-2-0-pro", "owned_by": "volcengine",
     "kind": "chat", "context": "256K", "source": "ark:volcengine",
     "note": "已宣布 2026-11-24 退役，不要作主推。"},
    {"id": "doubao-seed-2.0-lite", "ark_id": "doubao-seed-2-0-lite", "owned_by": "volcengine",
     "kind": "chat", "context": "256K", "source": "ark:volcengine",
     "note": "Seed 2.0 轻量，全模态理解。"},
    {"id": "doubao-seed-2.0-mini", "ark_id": "doubao-seed-2-0-mini", "owned_by": "volcengine",
     "kind": "chat", "context": "256K", "source": "ark:volcengine",
     "note": "Seed 2.0 最小档，低延迟高并发。"},
    {"id": "doubao-seed-2.0-code", "ark_id": "doubao-seed-2-0-code-preview-260215", "owned_by": "volcengine",
     "kind": "chat", "context": "256K", "source": "ark:volcengine",
     "note": "编程专用，已宣布 2026-11-24 退役，替代为 Seed Evolving。"},
    {"id": "doubao-seed-1.6-thinking", "ark_id": "doubao-seed-1-6-thinking-250715", "owned_by": "volcengine",
     "kind": "chat", "context": "未核实", "source": "wang:README ARK参考表",
     "note": "上一代深度推理。"},
    {"id": "doubao-seed-1.6-flash", "ark_id": "doubao-seed-1-6-flash-250615", "owned_by": "volcengine",
     "kind": "chat", "context": "未核实", "source": "wang:README ARK参考表",
     "note": "上一代快速推理。"},
    {"id": "doubao-1.5-pro-32k", "ark_id": "doubao-1-5-pro-32k-250115", "owned_by": "volcengine",
     "kind": "chat", "context": "32K", "source": "wang:README ARK参考表",
     "note": "上一代主力。"},
    {"id": "seedream", "ark_id": "seedream", "owned_by": "volcengine",
     "kind": "image", "context": "-", "source": "ark:volcengine",
     "note": "生图模型家族（Seedream 5.0 Pro 等）；网页端生图走 doubao-image，不直接等同。"},
    {"id": "seedance-2.0", "ark_id": "doubao-seedance-2-0", "owned_by": "volcengine",
     "kind": "video", "context": "-", "source": "ark:volcengine",
     "note": "视频生成；网页端走 doubao-video。免费额度动态调整，以账号页面为准。"},
    {"id": "seedance-2.5", "ark_id": "doubao-seedance-2-5", "owned_by": "volcengine",
     "kind": "video", "context": "-", "source": "ark:volcengine",
     "note": "视频生成新版，4~30 秒，全模态参考输入。网页端是否已接，待实测。"},
    {"id": "seed-audio-1.0", "ark_id": "seed-audio-1-0", "owned_by": "volcengine",
     "kind": "audio", "context": "-", "source": "ark:联网查 2026-06",
     "note": "语音/音乐/环境音，联网信源称 invite-only beta，待核实。"},
]


def list_models_payload() -> dict:
    """OpenAI-compatible /v1/models payload.

    `data` holds only web-routable models. ARK references are returned
    separately so no client mistakes them for routable web models.
    """
    return {
        "object": "list",
        "data": [
            {"id": m["id"], "object": "model", "owned_by": m["owned_by"], "created": 0}
            for m in WEB_MODELS
        ],
        "reference_models": [
            {**r, "web_routable": False, "bot_id": None} for r in REFERENCE_MODELS
        ],
    }
