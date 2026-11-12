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
     "model_item_key": "0", "mode_id": "1", "agent_mode": 2, "conversation_mode": 1,
     "reasoning_effort": 3, "reasoning_effort_levels": [3, 4, 5], "item_id": 0,
     "model_extra_params": {}, "verified_routing": False,
     "note": "快速模式（Hu410 doubao-fast 档案）。旧纯HTTP client.py 的 DEFAULT_BOT_ID 是另一值 7234781073513644036，待账号实测钉死。"},
    {"id": "doubao-pro", "owned_by": "doubao", "kind": "chat", "deep_think": 0,
     "bot_id": "7338286299411103781", "source": "wang:unified_server/CHAT_MODELS",
     "model_item_key": "0", "mode_id": "1", "agent_mode": 2, "conversation_mode": 1,
     "reasoning_effort": 3, "reasoning_effort_levels": [3, 4, 5], "item_id": 0,
     "model_extra_params": {}, "verified_routing": False,
     "note": "doubao 的别名，同为 need_deep_think=0，Hu410 key 同为 0。"},
    {"id": "doubao-think", "owned_by": "doubao", "kind": "chat", "deep_think": 1,
     "bot_id": "7338286299411103781", "source": "wang:unified_server/CHAT_MODELS",
     "model_item_key": "3", "mode_id": "1", "agent_mode": 2, "conversation_mode": 1,
     "reasoning_effort": 4, "reasoning_effort_levels": [3, 4, 5], "item_id": 3,
     "model_extra_params": {}, "verified_routing": False,
     "note": "思考模式（Hu410 doubao-turbo 档案），带思维链 reasoning_content（block_type 10040+10000）。"},
    {"id": "doubao-expert", "owned_by": "doubao", "kind": "chat", "deep_think": 3,
     "bot_id": "7338286299411103781", "source": "wang:unified_server/CHAT_MODELS",
     "model_item_key": None, "mode_id": "1", "agent_mode": 2, "conversation_mode": 1,
     "reasoning_effort": None, "reasoning_effort_levels": [3, 4, 5], "item_id": None,
     "model_extra_params": {}, "verified_routing": False,
     "note": "专家模式 use_auto_cot；额度耗尽自动降级到 doubao-think（ExpertQuotaTracker）。Hu410 无对应 key，请求走 wang need_deep_think=3 路，待账号实测钉死。"},
    {"id": "doubao-pro-chat", "owned_by": "doubao", "kind": "chat", "deep_think": 0,
     "bot_id": "7338286299411103781", "source": "lza6:config/MODEL_MAPPING",
     "model_item_key": None, "mode_id": "1", "agent_mode": 2, "conversation_mode": 1,
     "reasoning_effort": None, "reasoning_effort_levels": [3, 4, 5], "item_id": None,
     "model_extra_params": {}, "verified_routing": False,
     "note": "lzA6 唯一模型名，映射同一 Bot ID；整合版作 doubao-pro 的别名。lzA6 只给 bot_id，无 model_item_key，待账号实测钉死。"},
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

# --- Doubao Work / 工作任务模式 (mode_id 3, agent_mode 1) ---
# 来源：未登录 GET https://www.doubao.com/chat（2026-11-13 00:21 CST），页面
# 内嵌 window._ROUTER_DATA menuConfV2 全量目录；抽取见
# ../sources/doubaowork-client/evidence/model_table_20261113.json，详见
# ../reports/doubaowork-client-deepdive-20261113.md §1。
# 路由 = 单一 bot_id 7338286299411103781 + model_item_key（请求体三处：
# option.conversation_init_ext / option.model_config / option.aggregate_params）
# + agent_mode + conversation_mode + reasoning_effort + model_extra_params。
# Hu410/Doubao2api 已按同一 schema 实现 POST /chat/completion（2026-09 抓包）。
# 全部 10 个模型 verified_routing=False：key 是真的（公开页可重复抓取），但
# “登录后调了就通”尚未验证，见 README 待实测项。计费倍率是豆包工作模型选择页
# 标注的额度消耗倍率（11-12 官宣 + 截图），DeepSeek V4 Pro 与“自动”无倍率：
# 前者未查到，后者为“小额免费，按任务规模自动匹配”。
# 注意：item_id 10001 在全部第三方模型上相同，不是路由标识，别用它区分模型。
WORK_MODELS = [
    {"id": "doubao-work-auto", "owned_by": "doubao", "kind": "chat", "deep_think": None,
     "bot_id": "7338286299411103781", "source": "doubao.com/chat _ROUTER_DATA menuConfV2 2026-11-13",
     "model_item_key": "9", "mode_id": "3", "agent_mode": 1, "conversation_mode": 1,
     "reasoning_effort": 8, "reasoning_effort_levels": [3, 8, 5], "item_id": 9,
     "model_extra_params": {"total_window_size": "256000"}, "verified_routing": False,
     "billing_multiplier": None,
     "note": "工作任务默认模型“自动”：小额免费，系统按任务规模自动匹配模型，复杂时手动切才按倍率计费。"},
    {"id": "doubao-2.1-lite", "owned_by": "doubao", "kind": "chat", "deep_think": None,
     "bot_id": "7338286299411103781", "source": "doubao.com/chat _ROUTER_DATA menuConfV2 2026-11-13",
     "model_item_key": "seed-lite-7b", "mode_id": "3", "agent_mode": 1, "conversation_mode": 1,
     "reasoning_effort": 5, "reasoning_effort_levels": [3, 4, 5], "item_id": 10001,
     "model_extra_params": {"memory_profile": "256k", "total_window_size": "256000"}, "verified_routing": False,
     "billing_multiplier": "0.01x",
     "note": "豆包 2.1 Lite，限时优惠 0.01x。Hu410 doubao-lite 同 key。"},
    {"id": "doubao-2.1-pro", "owned_by": "doubao", "kind": "chat", "deep_think": None,
     "bot_id": "7338286299411103781", "source": "doubao.com/chat _ROUTER_DATA menuConfV2 2026-11-13",
     "model_item_key": "5", "mode_id": "3", "agent_mode": 1, "conversation_mode": 1,
     "reasoning_effort": 5, "reasoning_effort_levels": [3, 4, 5], "item_id": 5,
     "model_extra_params": {"total_window_size": "256000"}, "verified_routing": False,
     "billing_multiplier": "0.65x",
     "note": "豆包 2.1 Pro，0.65x。need_login: true。Hu410 doubao-pro 同 key。"},
    {"id": "deepseek-v4.1-flash", "owned_by": "deepseek", "kind": "chat", "deep_think": None,
     "bot_id": "7338286299411103781", "source": "doubao.com/chat _ROUTER_DATA menuConfV2 2026-11-13",
     "model_item_key": "person-deepseek-v4-1-flash-261017", "mode_id": "3", "agent_mode": 1, "conversation_mode": 1,
     "reasoning_effort": 5, "reasoning_effort_levels": [3, 4, 5, 6, 7], "item_id": 10001,
     "model_extra_params": {"memory_profile": "300k_230", "total_window_size": "300000"}, "verified_routing": False,
     "billing_multiplier": "0.01x",
     "note": "DeepSeek V4.1 Flash，11-12 首批第三方模型，限时优惠 0.01x。key 后缀 261017 与方舟 ID 碰巧一致，以本页为准。"},
    {"id": "kimi-k3.1-pro", "owned_by": "moonshot", "kind": "chat", "deep_think": None,
     "bot_id": "7338286299411103781", "source": "doubao.com/chat _ROUTER_DATA menuConfV2 2026-11-13",
     "model_item_key": "person-kimi-k3-1-pro-261111", "mode_id": "3", "agent_mode": 1, "conversation_mode": 1,
     "reasoning_effort": 5, "reasoning_effort_levels": [3, 4, 5, 6, 7], "item_id": 10001,
     "model_extra_params": {"memory_profile": "300k_230", "total_window_size": "300000"}, "verified_routing": False,
     "billing_multiplier": "0.95x",
     "note": "Kimi K3.1 Pro，11-12 首批第三方模型，0.95x。key 后缀 261111 与方舟 261024 不同，方舟 ID 不能代入。"},
    {"id": "kimi-k3.1-pro-highspeed", "owned_by": "moonshot", "kind": "chat", "deep_think": None,
     "bot_id": "7338286299411103781", "source": "doubao.com/chat _ROUTER_DATA menuConfV2 2026-11-13",
     "model_item_key": "person-kimi-k3-1-pro-highspeed-261111", "mode_id": "3", "agent_mode": 1, "conversation_mode": 1,
     "reasoning_effort": 5, "reasoning_effort_levels": [3, 4, 5, 6, 7], "item_id": 10001,
     "model_extra_params": {"memory_profile": "300k_230", "total_window_size": "300000"}, "verified_routing": False,
     "billing_multiplier": "1.44x",
     "note": "Kimi K3.1 Pro 高速，1.44x。截图有，11-12 通稿首批名单无。Magpie 插件称其为 kimi-k3.1-pro-fast。"},
    {"id": "kimi-k3", "owned_by": "moonshot", "kind": "chat", "deep_think": None,
     "bot_id": "7338286299411103781", "source": "doubao.com/chat _ROUTER_DATA menuConfV2 2026-11-13",
     "model_item_key": "person-kimi-k3-261111", "mode_id": "3", "agent_mode": 1, "conversation_mode": 1,
     "reasoning_effort": 5, "reasoning_effort_levels": [3, 4, 5, 6, 7], "item_id": 10001,
     "model_extra_params": {"memory_profile": "300k_230", "total_window_size": "300000"}, "verified_routing": False,
     "billing_multiplier": "1.48x",
     "note": "Kimi K3，1.48x。截图有，11-12 通稿首批名单无。"},
    {"id": "glm-5.3", "owned_by": "zhipu", "kind": "chat", "deep_think": None,
     "bot_id": "7338286299411103781", "source": "doubao.com/chat _ROUTER_DATA menuConfV2 2026-11-13",
     "model_item_key": "person-glm-5-3-261111", "mode_id": "3", "agent_mode": 1, "conversation_mode": 1,
     "reasoning_effort": 5, "reasoning_effort_levels": [3, 5, 7], "item_id": 10001,
     "model_extra_params": {"memory_profile": "300k_230", "total_window_size": "300000"}, "verified_routing": False,
     "billing_multiplier": "0.80x",
     "note": "GLM 5.3，11-12 首批第三方模型，0.80x。推理档位只有 3/5/7，没有 4 和 6。key 后缀 261111 与方舟不同。"},
    {"id": "glm-5.3-flash", "owned_by": "zhipu", "kind": "chat", "deep_think": None,
     "bot_id": "7338286299411103781", "source": "doubao.com/chat _ROUTER_DATA menuConfV2 2026-11-13",
     "model_item_key": "person-glm-5-3-flash-261111", "mode_id": "3", "agent_mode": 1, "conversation_mode": 1,
     "reasoning_effort": 5, "reasoning_effort_levels": [3, 5, 7], "item_id": 10001,
     "model_extra_params": {"memory_profile": "300k_230", "total_window_size": "300000"}, "verified_routing": False,
     "billing_multiplier": "0.08x",
     "note": "GLM 5.3 Flash，0.08x。截图有，11-12 通稿首批名单无。推理档位只有 3/5/7。"},
    {"id": "deepseek-v4-pro", "owned_by": "deepseek", "kind": "chat", "deep_think": None,
     "bot_id": "7338286299411103781", "source": "doubao.com/chat _ROUTER_DATA menuConfV2 2026-11-13",
     "model_item_key": "person-deepseek-v4-pro-ga-260813", "mode_id": "3", "agent_mode": 1, "conversation_mode": 1,
     "reasoning_effort": 5, "reasoning_effort_levels": [3, 4, 5, 6, 7], "item_id": 10001,
     "model_extra_params": {"memory_profile": "300k_230", "total_window_size": "300000"}, "verified_routing": False,
     "billing_multiplier": None,
     "note": "DeepSeek V4 Pro。截图里没有，网页目录里有第 10 个。计费倍率未查到，不编。"},
]

WEB_MODELS.extend(WORK_MODELS)

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


def find_model(model_id: str):
    """Return the WEB_MODELS entry for `model_id`, or None."""
    for m in WEB_MODELS:
        if m["id"] == model_id:
            return m
    return None


def list_models_payload() -> dict:
    """OpenAI-compatible /v1/models payload.

    `data` holds only web-routable models. ARK references are returned
    separately so no client mistakes them for routable web models.
    Each routable entry also carries its routing profile
    (`model_item_key` / `agent_mode` / `conversation_mode` /
    `reasoning_effort` / `verified_routing`): `verified_routing` is False
    for every model until a logged-in account has actually called it
    successfully -- a routing key taken from a public page is not a
    verified route. Clients must not treat an unverified model as working.
    """
    data = []
    for m in WEB_MODELS:
        entry = {"id": m["id"], "object": "model", "owned_by": m["owned_by"], "created": 0,
                 "verified_routing": bool(m.get("verified_routing", False))}
        if m.get("model_item_key") is not None:
            entry["model_item_key"] = m["model_item_key"]
            entry["agent_mode"] = m.get("agent_mode")
            entry["conversation_mode"] = m.get("conversation_mode")
            entry["reasoning_effort"] = m.get("reasoning_effort")
        if "billing_multiplier" in m:
            entry["billing_multiplier"] = m["billing_multiplier"]
        data.append(entry)
    return {
        "object": "list",
        "data": data,
        "routing_verified_count": sum(1 for m in WEB_MODELS if m.get("verified_routing")),
        "note": ("verified_routing=false 表示路由 key 来自公开资料、尚未经登录账号实测放行，"
                 "不是已通模型。原生聊天 SSE 只有文本块，没有原生 tool_calls。"),
        "reference_models": [
            {**r, "web_routable": False, "bot_id": None} for r in REFERENCE_MODELS
        ],
    }
