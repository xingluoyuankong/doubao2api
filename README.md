# doubao2api-unified

豆包 + 通义千问网页端反代整合版。主路径 wang 纯 HTTP，lzA6 Playwright `a_bogus` 签名只做单次兜底。

> **状态：已部署 AWS 悉尼，域名 `doubao2api.xzxyuan.l.cd`，无账号实测。** 仓库 `xingluoyuankong/doubao2api`，服务端口 127.0.0.1:8793。无账号时 `/health` 为 `not_ready`，聊天/生图一律 401，账号实测待主人提供豆包账号后做。

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

## 模型

`/v1/models` 返回可路由模型 24 个（豆包 8 + 通义 16），另附 `reference_models`（火山方舟 ARK 参考，不可网页路由，不编造 bot_id）。完整清单见 `../reports/models-20261112.md`。

## 设计

见 [DESIGN.md](DESIGN.md)。部署草稿在 `deploy/`（systemd + nginx，未安装）。
