# doubao2api-unified

豆包 + 通义千问网页端反代整合版。主路径 wang 纯 HTTP，lzA6 Playwright `a_bogus` 签名只做单次兜底；聊天上游按 Hu410 协议走 `POST /chat/completion`（`doubao_client.py`）。

> **状态：已部署 AWS 悉尼，域名 `doubao2api.xzxyuan.l.cd`，无账号实测。** 仓库 `xingluoyuankong/doubao2api`，服务端口 127.0.0.1:8793。无账号时 `/health` 为 `not_ready`，聊天/生图一律 401，账号实测待主人提供豆包账号后做。

## 工作任务模型（2026-11-13 新增，v0.2.0）

豆包工作 11 月 12 日官宣接入第三方模型。路由标识来自未登录 `GET https://www.doubao.com/chat` 的页面内嵌 `window._ROUTER_DATA`（`menuConfV2`，2026-11-13 00:21 抓取，`pc_version 3.45.5`），抽取见 `../sources/doubaowork-client/evidence/model_table_20261113.json`，深挖报告见 `../reports/doubaowork-client-deepdive-20261113.md`。

路由 = 单一 `bot_id 7338286299411103781` + `model_item_key`（请求体三处：`option.conversation_init_ext` / `option.model_config` / `option.aggregate_params`）+ `agent_mode=1` + `conversation_mode=1` + `reasoning_effort` + `model_extra_params`。第三方 key 格式 `person-<模型>-<日期>`，Kimi/GLM 后缀 `261111` 与火山方舟 `261024` 不同，方舟 ID 不能代入。

| 模型 | model_item_key | 倍率 |
|---|---|---|
| doubao-work-auto（自动） | `9` | 小额免费 |
| doubao-2.1-lite | `seed-lite-7b` | 0.01x |
| doubao-2.1-pro | `5` | 0.65x |
| deepseek-v4.1-flash | `person-deepseek-v4-1-flash-261017` | 0.01x |
| kimi-k3.1-pro | `person-kimi-k3-1-pro-261111` | 0.95x |
| kimi-k3.1-pro-highspeed | `person-kimi-k3-1-pro-highspeed-261111` | 1.44x |
| kimi-k3 | `person-kimi-k3-261111` | 1.48x |
| glm-5.3 | `person-glm-5-3-261111` | 0.80x |
| glm-5.3-flash | `person-glm-5-3-flash-261111` | 0.08x |
| deepseek-v4-pro | `person-deepseek-v4-pro-ga-260813` | 未查到 |

**诚实标注：** 全部 10 个新模型在 `/v1/models` 里 `verified_routing=false`。key 是真的（公开页可重复抓取），但“登录后调了就通”尚未验证，不要把未实测模型当已通模型。

**上限（别指望绕过）：** 原生聊天 SSE 回包只有文本块，没有原生 `tool_calls`。编程软件要“客户端定义工具 → 上游返回结构化 tool call → 客户端执行”的循环，两条路（原生 API 路、Magpie UI 驱动路）都给不了，天花板是文本仿真（Magpie 的 `<tool_call>` 提示词格式）。另外多轮对话会被压平成一条文本发过去，不保留真多轮会话状态；`aggregate_params.mode_id` 与 `provider_id` 按 Hu410 抓包发空字符串，是否要填 `mode_id="3"` / 非空 `provider_id` 待登录后实测确认。

## 待实测（需登录账号）

1. `POST /v1/session/verify`：用已存会话向 `doubao` 发一次 "hi"，上游真返回 200 才置 `verified=true`；失败返回 502，会话保持未验证。
2. 逐模型登录后最短请求放行验证：工作任务 10 个模型各发一次，看 HTTP 状态、SSE 事件、失败业务码；重点确认第三方模型是否要求付费订阅、`mode_id` 填 `""` 还是 `"3"`、`provider_id` 是否要填非空。
3. 工具调用链路最终结论：在回包里找 tool call 形态，按现有证据预期是没有；若实测证实没有，“编程软件原生 tool call”正式判死刑，只剩文本仿真。
4. 签名兜底单次验证：纯 HTTP 撞签名/风控类失败时，Playwright `frontierSign` 拉起一次算 `a_bogus` 重发一次。
5. 钉死 Bot ID：旧纯 HTTP `client.py` 的 `7234781073513644036` 与统一服务的 `7338286299411103781` 两值并存，实测对比返回再定。

## 快速开始（本地骨架）

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest tests/ -q
DOUBAO_PORT=8793 .venv/bin/uvicorn app:app --host 127.0.0.1 --port 8793
curl http://127.0.0.1:8793/health
curl http://127.0.0.1:8793/v1/models
```

无账号时 `/health` 为 `not_ready`，聊天/生图一律 401 `not_logged_in`，绝不伪造成功。

## 登录（三种入口，待主人提供账号）

| 入口 | 端点 | 说明 |
|---|---|---|
| QR 扫码 | `POST /v1/session/qr-login` | wang 流程，部署态接 Playwright；骨架明确 503 |
| Cookie 导入 | `POST /v1/session/cookie {"sessionid": "..."}` | 存 0600 会话文件，`verified:false` |
| 会话导入 | `POST /v1/session/import {"cookies": {...}, "params": {...}}` | 导入已登录浏览器会话；豆包无公开 OAuth 客户端流程，此口即该路径 |
| 会话验证 | `POST /v1/session/verify {"model": "doubao"}` | 向已存会话发一次最小上游调用（"hi"），真返回 200 才置 `verified=true`；失败 502，会话保持未验证 |

## 模型

`/v1/models` 返回可路由模型 34 个（豆包 8 + 通义 16 + 工作任务 10），另附 `reference_models`（火山方舟 ARK 参考，不可网页路由，不编造 bot_id）。完整清单见 `../reports/models-20261112.md` 与 `../reports/doubaowork-client-deepdive-20261113.md`。每个可路由模型带 `model_item_key` / `agent_mode` / `conversation_mode` / `reasoning_effort` / `verified_routing` / `billing_multiplier`（新模型才有倍率字段）。

聊天请求按模型档案构建上游请求体（见 `doubao_client.py:build_completion_request`）：有 `model_item_key` 的模型写三处，无 key 的 wang 旧模型（doubao-expert、doubao-pro-chat）走 `need_deep_think`。未知模型 400 `model_not_found`，非聊天模型走聊天端点 400 `model_not_chat`。

## 设计

见 [DESIGN.md](DESIGN.md)。部署草稿在 `deploy/`（systemd + nginx，未安装）。
