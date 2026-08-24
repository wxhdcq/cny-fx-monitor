# 折光 · 人民币汇率监测器

面向 Oracle Cloud Ampere A1（4 OCPU / 24GB）的人民币汇率监测 MVP。系统自动同步全球法币参考汇率，统一换算为“1 外币 = X CNY”，并为主流货币、订阅低价区和高风险货币提供独立视图。

> 当前数据源 Frankfurter v2 主要是央行日度参考汇率，不是交易级实时行情，也不代表银行、银行卡或订阅平台的实际结算价。

## 主要功能

- 自动同步数据源支持的全部有效法币，并排除贵金属和特别提款权；
- 自动检查历史跨度，不足一年时回填 370 天日线；
- 主流、订阅低价区、高风险三类标签；
- 24 小时、3 个月、6 个月和 1 年涨跌及风险分计算；
- 3/6/12 个月历史汇率 SVG 曲线；
- 任意双币种即时换算，默认从 100 CNY 开始；
- 国家/地区旗帜与浏览器本地自选置顶；
- 24 小时快速贬值告警规则；
- 数据源健康状态；
- Telegram 告警接口；
- 中文响应式看板；
- SQLite 本地运行和 PostgreSQL Docker 部署；
- 管理员令牌保护的手动采集接口。

## 本地运行

需要 Python 3.12 或更高版本。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Copy-Item .env.example .env
.\.venv\Scripts\uvicorn.exe app.main:app --reload
```

打开 <http://127.0.0.1:8000>。首次启动后采集任务会在后台执行，通常几秒内完成；如页面尚无数据，可稍后刷新。

## Oracle / Docker 部署

1. 安装支持 ARM64 的 Docker Engine 和 Compose 插件。
2. 创建 `.env`，至少修改 `POSTGRES_PASSWORD` 和 `ADMIN_TOKEN`。
3. 启动服务：

```bash
docker compose up -d --build
docker compose ps
curl http://127.0.0.1:8765/health
```

默认仅绑定服务器回环地址 `127.0.0.1:8765`，不会直接暴露到公网。正式公网部署应在前面增加 Caddy、Nginx 或 OpenResty HTTPS 反向代理，并仅开放 80/443。仓库提供了可挂载到 `/fx-monitor/` 子路径的 [OpenResty 配置](deploy/nginx-fx-monitor.conf)。

## 配置项

| 变量 | 默认值 | 说明 |
|---|---|---|
| `DATABASE_URL` | SQLite | 数据库连接地址 |
| `COLLECT_INTERVAL_MINUTES` | `60` | 采集间隔，最低 5 分钟；日度源频繁采集不会产生新行情 |
| `APP_PORT` | `8765` | Docker 在服务器回环地址绑定的端口 |
| `ADMIN_TOKEN` | 空 | 手动采集接口令牌，生产环境必须设置 |
| `TELEGRAM_BOT_TOKEN` | 空 | Telegram Bot Token |
| `TELEGRAM_CHAT_ID` | 空 | Telegram 接收目标 |

手动触发采集：

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/collect -Headers @{ 'X-Admin-Token' = 'your-token' }
```

## API

- `GET /health`：服务和数据源状态；
- `GET /api/summary`：市场摘要；
- `GET /api/rates`：全部最新汇率；
- `GET /api/rates?tag=high-risk`：高风险货币；
- `GET /api/rates/{code}/history?days=370`：单币历史；
- `GET /api/alerts`：告警记录；
- `POST /api/collect`：管理员手动采集。

## 当前限制

- 当前只有日度参考行情，24 小时变化按最近两个可用日度样本计算；
- 高风险国家的官方价可能与实际兑换价严重脱节；
- 暂未接入分钟级商业 API、CFETS 官方中间价和第二数据源偏差检测；
- 初版通过 `create_all` 建表，正式多版本升级前应增加 Alembic 迁移。

版本变化见 [CHANGELOG.md](CHANGELOG.md)。

旗帜 SVG 来自 [flag-icons](https://github.com/lipis/flag-icons)，按 MIT License 随项目本地托管，避免不同操作系统对旗帜 Emoji 的渲染差异。
