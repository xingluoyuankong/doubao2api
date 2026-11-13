# doubao2api-unified

豆包 + 通义千问网页端反代整合版。主路径 wang 纯 HTTP，lzA6 Playwright `a_bogus` 签名只做单次兜底；聊天上游按 Hu410 协议走 `POST /chat/completion`（`doubao_client.py`）。

> **状态：已部署 AWS 悉尼，域名 `doubao2api.xzxyuan.l.cd`，无账号实测。** 仓库 `xingluoyuankong/doubao2api`，服务端口 127.0.0.1:8793。无账号时 `/health` 为 `not_ready`，聊天/生图一律 401，账号实测待主人提供豆包账号后做。

## 管理员鉴权（2026-11-13 新增，v0.2.2）

控制台此前任何人打开就能用，已锁上。账号固定 `admin`，密码只以 SHA-256 摘要形式存在服务器 `.env`（`DOUBAO2API_ADMIN_PASSWORD_SHA256`），明文密码与摘要都不进仓库、不进代码、不进 README。登录页是前端原生表单，不是浏览器弹框 Basic Auth。

- 未登录时：`GET /` 返回登录页（`static/login.html`）；`GET /static/index.html`、`/v1/chat/completions`、`/v1/session/*`、`GET /v1/session/status`、`GET /admin`、全部生图/视频/音频/文件端点一律 401。
- 公开不动：`GET /health`、`GET /v1/models` 仍公开（newapi 读模型目录和健康检查要用）。
- 登录成功发 7 天 HttpOnly session cookie（随机 token，只存内存，重启重登）；`POST /auth/logout` 登出。登录失败统一显示“账号或密码错误”，不区分账号错还是密码错；同一 IP 连续 5 次错锁 10 分钟（防爆破锁，不是限流）。
- 本地测试时在环境变量里设摘要再跑 pytest，见 `tests/test_smoke.py` 顶部。

## 前端控制台（2026-11-13 新增，v0.2.1）

根路径 `/` 返回控制台（单文件 `static/index.html`，内联 CSS/JS，不依赖外部 CDN）。内容：服务状态（`/health`）、模型列表（34 个，分豆包聊天 / 豆包工作 10 个 / 通义千问 / 生成模型四组，带 `model_item_key`、倍率、`verified_routing` 标注）、登录区（扫码登录、Cookie 导入、会话导入，对应现有后端接口）、验证按钮（`POST /v1/session/verify`）、聊天测试区（选模型发一句话，无账号显示 401 不伪造成功）。后端只加了 `/` 与 `/static/*` 两个路由，现有 API 一字未动。

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

**上限（说清楚，不认命）：** 原生聊天 SSE 回包只有文本块，没有原生 `tool_calls` 通道——这一点是真的，三家独立项目一致证实（见 `reports/toolcall-ceiling-break-20261113.md`）。但“没有原生通道”不等于“编程软件用不了工具循环”：本网关已按 wang 的已验证做法实现了文本仿真工具循环（见下节“工具调用”），Claude Code / Codex / OpenCode 发 OpenAI `tools` 就能拿到 `tool_calls`、执行完把结果发回来继续循环。模型本身的原生 Function Calling 只存在于付费的火山方舟 API，不属于这条网页反代通道。另外多轮对话会被压平成一条文本发过去，不保留真多轮会话状态；`aggregate_params.mode_id` 与 `provider_id` 按 Hu410 抓包发空字符串，是否要填 `mode_id="3"` / 非空 `provider_id` 待登录后实测确认。

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

## 工具调用（Tool Calling，文本仿真循环）

`POST /v1/chat/completions` 接受 OpenAI `tools` / `tool_choice` / `parallel_tool_calls`（实现在 `tool_calling.py`，移植自 wang `doubao2api/tool_calling.py`，Apache 2.0）：

- 有 `tools` 且 `tool_choice != "none"` 时，工具定义以 `<tool_call>` 提示词格式注入，模型回的 `<tool_call>` 块被解析回 OpenAI `tool_calls`，`finish_reason` 为 `tool_calls`；流式同样以 `tool_calls` delta 发出。`tool_choice: "required"` / 指定函数名会强制要求调用；`"none"` 则不注入工具。
- **循环是客户端驱动的**（OpenAI 协议标准）：客户端执行工具后把 `role: tool` 结果发回来，下一次请求网关再把工具定义、历史（含重建的 `<tool_call>` 与 `[工具调用结果]`）喂给豆包。网关不替客户端执行工具，也不内部死循环。
- 轮数上限：`DOUBAO_TOOL_MAX_ROUNDS`（默认 5，可配），超过后最旧的工具轮次从展平后的提示词里丢掉（留标记、记日志），原始任务永远保留；单条工具结果截断 12000 字符，提示词总预算 70000 字符（`DOUBAO_TOOL_MAX_PROMPT_CHARS`）。
- 截断续接：模型在 `<tool_call>` 中间被截断时，网关自动续接一次（去重拼接），再解析；解析不到的完整块会原样当文本回给客户端，绝不吞掉。
- 不在客户端工具列表里的工具名会被过滤掉并记日志；参数名按 wang 的映射表自动纠正（如 `cmd` → `command`）。
- 诚实边界：这是文本仿真，不是上游原生通道。wang 对千问路线的 live 验证是“思考+工具共存，已验证可用”；豆包路线用同一模块，但本网关尚未用登录账号对上游实测过各模型的工具调用成功率——见 `reports/toolcall-ceiling-break-20261113.md`。

## 设计

见 [DESIGN.md](DESIGN.md)。部署草稿在 `deploy/`（systemd + nginx，未安装）。
