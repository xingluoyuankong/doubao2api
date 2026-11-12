# doubao2api-unified — 整合设计

> 状态：2026-11-12 22:0x CST，沙箱本地骨架，未部署、未推送、未实测上游。
> 目标仓库（待创建）：`xingluoyuankong/doubao2api`（2026-11-12 实查：该名未被占用，见 reports/github-20261112.md）。
> 部署目标：AWS 悉尼 16.176.174.27，域名 `doubao2api.xzxyuan.l.cd`（DNS 待浏览器面板加 A 记录，主人确认后做）。
> 账号：待主人提供（扫码 / OAuth·会话导入 / Cookie 三种入口均已备好，见 §5）。**无账号前不做聊天/生图实测。**

## 1. 结论先行（实测）

- **主路径 = wang 版的纯 HTTP 客户端 `DoubaoChatClient`（`sources/wang/doubao2api/client.py`，2360 行）。**
  但必须纠正上一轮的说法：wang 最新版（commit `95beb0788338ba268e13ca4c80890ceeae6ff055`，2026-05-25）**统一服务的主路径已经是 `BrowserClient`**（`sources/wang/doubao2api/browser_client.py`，1748 行），README 明写“当前统一服务主路径使用 `BrowserClient`，默认 Bot ID 为 `7338286299411103781`”，`client.py` 只保留旧版常量。整合版不照搬这个演变：**把纯 HTTP 客户端扶回主路径**，浏览器只做兜底，理由见 §2。
- **兜底 = lzA6 版的 Playwright 签名服务**（`sources/lza6/app/services/playwright_manager.py`，187 行）：浏览器只跑 `window.byted_acrawler.frontierSign` 生成 `a_bogus`，请求本身仍由 httpx 发。**只在 wang 纯 HTTP 返回签名/风控类失败时调用一次，失败即回落报错，不死循环、不常驻浏览器。**
- **lzA6 其余部分不采用**：它只有 1 个模型（`doubao-pro-chat`）、只有聊天两个端点、无多模态、无 Admin、无文件/生图/视频/音乐；Python 代码总计仅 776 行，6 个提交、最后提交 2025-10-20，已一年无更新。
- **wang 的 Qianwen 分支直接继承**：`qianwen_client.py` 已内置通义千问（Playwright 浏览器内 fetch，`qwenSign/etSign/bx-ua`），16 个模型 id。这是“不止 doubao”的第一部分，第二部分是火山方舟 ARK 参考模型（只作参考列表，不走网页反代，见 `models.py` 与 reports/models-20261112.md）。
- **AWS 现状（2026-11-12 13:55 UTC 实测）**：2 核，内存总量 3832 MB、可用仅 899 MB、swap 已用 2895 MB；磁盘 `/` 77G 已用 67G、剩 9.8G（88%）；load 0.22/0.24/0.34；无在跑构建。**结论：纯 HTTP 主路径可行（约 50–150 MB），Playwright 常驻浏览器（300–800 MB）不可行，只能按需拉起、用完即关。** 建议端口 `127.0.0.1:8793`（实查空闲，8790 qoder / 8791 / 8792 trae 的下一位）。

## 2. 为什么主路径是纯 HTTP，而不是浏览器

| 维度 | wang 纯 HTTP `client.py` | wang `BrowserClient` / Sei / robin | lzA6 签名服务 |
|---|---|---|---|
| 资源 | 几十 MB，无浏览器 | 300–800 MB 常驻 Chromium | 浏览器只在签名时存在，但仍需 Chromium + 冷启动 30–60 秒 |
| 并发 | httpx 异步，可多路 | 单浏览器串行（Sei 自述） | 签名加全局锁，串行 |
| 稳定性 | 签名失效时直接失败（`a_bogus` 不自己算；msToken 可选，假值会触发风控） | 浏览器自动注入 `a_bogus/msToken`，最抗风控变化 | 折中：只把签名外包给浏览器 |
| 功能 | 最全：聊天/思考链/图/视频/音乐/文件 60+ 格式/1GB 文件中转 | 同样全（BrowserClient 复制了同一套） | 只有聊天 |
| 失效模式 | 上游改签名/端点即失效，需跟进逆向 | 上游改前端 JS 即失效，但通常比纯 HTTP 晚 | 签名函数 `frontierSign` 改名/失效即失效 |

整合策略就是取三者交集：**平时走最轻的纯 HTTP；撞签名/风控失败时，用 lzA6 的办法临时拉一个浏览器只算一次签名，重试一次；再失败就明确报错，不换号、不重试、不死循环。** 这与主人的“不加限制、不打包限制进修复”一致：兜底是单次、有上限、可观测的，不是静默重试。

## 3. 统一接口

| 端点 | 方法 | 主路径 | 无账号时行为 |
|---|---|---|---|
| `/health` | GET | 本地状态 | `{"status":"not_ready","logged_in":false,...}`，不伪造 ok |
| `/v1/models` | GET | 本地模型表 | 返回全部可路由模型 24 个 + ARK 参考列表（`reference_models`，标注不可网页路由） |
| `/v1/chat/completions` | POST | wang 纯 HTTP → 失败一次 → lzA6 签名兜底一次 | 无 sessionid → 401 `not_logged_in`；有 session 但未验证 → 503 `upstream_not_verified` |
| `/v1/images/generations` | POST | wang `/samantha/chat/completion` content_type=2009 系 | 同上 401/503 |
| `/v1/images/edits` | POST | wang 图生图 | 同上 |
| `/v1/videos/generations` | POST | wang Seedance 2.0 异步两步（`/samantha/chat/async/stream` 轮询） | 同上；额度按账号日限，耗尽即报，不静默换号 |
| `/v1/audio/generations` | POST | wang 音乐生成 content_type=2005 | 同上 |
| `/v1/files` | POST | wang 四步上传（prepare_upload → ImageX STS → TOS → get_file_url） | 同上 |
| `/v1/files/download` | GET | wang | 同上 |
| `/v1/images/upload` | POST | wang | 同上 |
| `/admin` | GET | 状态 JSON（骨架） | 不暴露凭证，只返预览/状态 |
| `/v1/session/qr-login` | POST/GET | wang QR（需 Playwright 部署态） | 骨架：503 `qr_login_unavailable_in_skeleton`，部署后接 wang 流程 |
| `/v1/session/cookie` | POST | Cookie 导入（sessionid） | 存 0600 会话文件，`verified:false`，不记日志 |
| `/v1/session/import` | POST | 会话文件导入（OAuth/已登录浏览器会话） | 同上；豆包无公开 OAuth 客户端流程，此口即“已登录会话导入” |
| `/v1/session/status` | GET | 本地 | `logged_in / verified / methods` |

认证：下游 `Authorization: Bearer <DOUBAO_API_KEY>`（wang `.env.example` 同款，留空则不鉴权；**部署时必须设**，nginx 不再另加 Basic Auth）。

## 4. 三模式与路由

- `need_deep_think`：0=快速 `doubao`，1=思考 `doubao-think`，3=专家 `doubao-expert`（`use_deep_think:true, use_auto_cot:true`），另有 2=auto（wang `client.py` 注释，未在 `/v1/models` 暴露，待实测）。
- 三模式共用同一个 Seed 模型，区别是 CoT 提示注入；专家额度耗尽会静默降级——整合版用 wang 的 `ExpertQuotaTracker`：连续 2 次专家请求无 reasoning 即标记 degraded，30 分钟后才重试专家，其余时间回落思考，并在 `/health` 暴露 `expert_degraded`。
- `seed_intention` 路由（wang README）：`seed_main/default|knowledge|writing`、`browsing/complex_browsing`、`multi_agent/Agent-Code`，由上游按内容意图分发，网关不改写。
- Bot ID（实查代码，两个值并存，**未解决，需账号实测钉死**）：
  - 旧纯 HTTP `client.py`：`DEFAULT_BOT_ID=7234781073513644036`，`EXTENSION_BOT_ID=7338286299411103781`（图片/文件/多媒体用后者）。
  - 统一服务 `BrowserClient` 与 lzA6：默认 `7338286299411103781`。
  - 整合版骨架默认用 `7338286299411103781`，并在实测时对比两个 Bot 的返回，写死前不改。

## 5. 登录：三种入口（都备好，都没账号）

1. **QR 扫码**：wang 流程——`GET https://www.doubao.com` 取 CSRF → `POST /passport/web/scan_qrcode/` 取码 → 豆包 App 扫码 → 取 `sessionid/ttwid/passport_csrf_token` → 注入 Playwright 持久化目录。骨架里路由已存在，部署态接 wang `BrowserClient` + `qr_login.py`；沙箱骨架无浏览器，明确 503，不伪造。
2. **Cookie 导入**：`POST /v1/session/cookie {"sessionid": "..."}` 或环境变量 `DOUBAO_COOKIE` / 会话文件 `.doubao_session.json`（wang `session.py` 同款加载顺序）。只存、不验、不记日志，文件 0600。
3. **OAuth / 会话导入**：豆包没有公开的 OAuth 客户端授权流程可供 2api 使用；可行路径是导入已登录浏览器的会话文件（cookies + device params `device_id/web_id/fp`）。`POST /v1/session/import` 即此口，同样只存、不验。

三种入口共用一条规则：**存下来 ≠ 已验证**。`verified` 只有在上游 `/chat/completion` 或 `/samantha/chat/completion` 真正返回 200 后才置 true，在此之前聊天一律 503。

## 6. 签名兜底（lzA6 派生，单次）

```
纯 HTTP 请求
  → 成功：返回
  → 失败且错误属于签名/风控类（401/403/a_bogus/msToken/风控关键词，待实测定阈值）
      → 拉起一次性 Playwright（headless，超时 30s）
          → 等 window.byted_acrawler.frontierSign 就绪
          → 参数按字母排序 + 静态设备指纹 + msToken，调 frontierSign 得 a_bogus
          → httpx 重发一次
          → 成功：返回；失败：报错，不再重试
      → Playwright 不可用/签名函数缺失：直接报 signing_unavailable
  → 失败且不属于签名类：直接报错，不走兜底
```

要点：兜底浏览器**用完即关**（AWS 内存只剩 899 MB 可用，常驻不起）；签名服务不缓存浏览器实例；整合版不带入任何上游现成的凭证值。

## 7. 多账号

- **wang 现状（实查）**：统一服务是单账号（单 `BrowserClient` + 单会话文件），无账号池；`session.py` 只支持单 Cookie/单文件。
- **lzA6 现状（实查）**：`CredentialManager` 对 `DOUBAO_COOKIE_1..N` 做简单轮询（`index=(index+1)%n`），`SessionManager` 是 TTLCache（1024 条，默认 3600s）；无健康检查、无失败退役、无额度感知。
- **整合版设计**：沿用 lzA6 的轮询思想，但加三条 wang 没有的：① 失败计数，连续失败即暂时跳过该账号（不删除）；② 视频额度按账号记，耗尽跳过该账号的视频请求、不禁聊天；③ 切换账号时会话 id 不跨账号搬运（Sei 的教训：会话绑定创建账号，跨号返 409）。多账号是 Phase 2，骨架先做单账号 + 接口预留，不先写复杂调度。

## 8. 工具调用

- **豆包网页模型不支持原生 Function Calling / Tool Use**（wang README 原话），不适合当编程智能体后端。
- wang 近期新增 `tool_calling.py`（1283 行）是 **prompt 注入 MVP**：把 OpenAI tools 转成系统提示里的 `<tool_call>{"name":...,"arguments":{...}}</tool_call>` 文本，让模型照格式输出，再解析回 OpenAI 格式。整合版**保留此模块、默认关闭**，只在调用方显式传 `tools` 且模型为 Qianwen（通义原生支持该格式）或用户确认时启用；不把它说成“豆包支持工具调用”。
- Qianwen 侧同理：`qianwen_client.py` 的工具调用走其自有格式，待实测。

## 9. 资源与部署草稿

- 部署：`/opt/doubao2api-unified`（待主人确认目录），Python 3.12 venv，systemd `doubao2api.service`（`WorkingDirectory` 指向部署目录，`ExecStart` 为 venv 内 uvicorn，`Restart=on-failure`，`MemoryMax=512M`，`CPUQuota=100%`——钉单核，按主人构建纪律）。
- 端口：`127.0.0.1:8793`（实查空闲；备选 7870，也空闲）。nginx 域名 `doubao2api.xzxyuan.l.cd`，模板照 `xhx2api`：`proxy_buffering off`、`proxy_request_buffering off`、`proxy_read_timeout 3600s`、`proxy_send_timeout 3600s`、`client_max_body_size 64m`（文件上传 1GB 在网关内走分片/流式，不放 nginx 大包，待实测定）。
- 构建纪律：构建前先查 `free/load/df/ss/docker ps`，无在跑构建才动手；Docker 构建钉 `cpuset=0 + --memory=1g`，绝不并行；磁盘只剩 9.8G，构建前先清悬空镜像（需主人点头，见 reports/aws-20261112.md）。
- DNS：`doubao2api.xzxyuan.l.cd` A → 16.176.174.27，**走 DNSHE 浏览器面板**，动手前面板读数与公网 DNS 交叉核对；DNSHE 双密钥 API 已死，不用。

## 10. 已知失效点（实查代码 + 联网）

1. wang 最后提交 2026-05-25，距今约 5.5 个月；期间豆包网页端已多次更新（Seed 2.1 于 2026-06-23 发布），`/chat/completion` 与 `/samantha/chat/completion` 的字段可能已漂移，**必须账号实测**。
2. lzA6 最后提交 2025-10-20，约 13 个月无更新；其 `pc_version 2.41.0 / version_code 20800` 大概率已过期，签名兜底能否工作待实测。
3. Seed 2.0 Pro 与 Seed 2.0 Code 已宣布 2026-11-24 退役（联网查），ARK 参考列表里已标注，不要再把它们当主推。
4. 视频免费额度动态收紧（多方信源：每日约 10 次 → 5 次 Fast/Mini，10 秒耗 2 次），以账号实测页面显示为准，不写死次数。
5. wang 的 `client.py` 与 `browser_client.py` 对同一端点的实现已分叉（`/chat/completion` 主用 vs `/samantha/chat/completion` 主用），整合时以账号实测的返回为准选主用端点，另一条作备用。

## 11. 待办（按顺序）

1. 主人确认：目标仓库名（已定 `xingluoyuankong/doubao2api`，待创建）、部署端口（建议 8793）、域名 DNS（浏览器面板加 A 记录）。
2. 主人提供豆包账号（三选一：扫码 / 会话导入 / Cookie）。
3. 账号实测：聊天三模式、思考链、文件问答、生图、视频、音乐、Qianwen 16 模型抽查；钉死 Bot ID 与主用端点。
4. 实测通过后：创建 `xingluoyuankong/doubao2api` 并推送整合版（private，参考其它 2api 仓库做法），再部署 AWS + nginx + 域名验证。
5. Phase 2：多账号池（失败跳过 + 视频额度感知）、专家降级观测、探针。
