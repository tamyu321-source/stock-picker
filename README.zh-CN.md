<p align="right">
  <a href="./README.md"><img src="https://flagcdn.com/w40/gb.png" alt="United Kingdom flag" width="22"> English</a> |
  <a href="./README.zh-TW.md"><img src="https://flagcdn.com/w40/tw.png" alt="Taiwan flag" width="22"> 繁體中文</a> |
  <a href="./README.nan-TW.md"><img src="./assets/taiwan-green-island.svg" alt="Green Taiwan island flag" width="22"> 臺語（ㄉㄞˊ ㄍㄧˋ）</a> |
  <a href="./README.zh-CN.md"><img src="https://flagcdn.com/w40/cn.png" alt="China flag" width="22"> 简体中文</a>
</p>

# Open Stock Picker

Open Stock Picker 是一个多语言、AI 辅助的股票研究 Web App。它的主要流程是无代码市场扫描：选择市场和策略后，让后端实时发现、评分并排序更高质量、适合投资研究的股票，覆盖中国、香港、新加坡、美国和台湾。

它面向真实研究流程设计，不是静态作品集展示。这个应用不会执行交易，也不会存储券商账号或凭证。

## 功能

- Vue 3 + Vite Web 界面，支持英文、简体中文和繁体中文 UI。
- Python Flask 后端，整合实时数据源和可解释评分模型。
- 不需要先输入股票代码，就可以直接扫描市场。
- 如果用户已经有特定股票，也可以选填股票代码或公司名称来缩小扫描范围。
- 自动探索市场股票池，而不是依赖硬编码股票列表。
- 通过 Yahoo Finance chart endpoints 获取实时价格历史；如果已安装 `yfinance`，也可以选择使用。
- 通过 Google News 和本地来源筛选进行分市场 RSS/新闻抓取，并在可用时使用公司名称和文章摘要。
- 内置平衡型、成长型和防御价值型投资策略。
- 自定义策略滑杆，可调整动量、估值、情绪、风险和质量权重。
- 生成买入、观察、卖出判断，并附带决策理由和来源链接。

## 架构

```text
Vue 3 web app
  -> /api/config       strategy, market, and default ticker metadata
  -> /api/analyze      live data fetch, RSS crawl, scoring, verdicts, explanations

Flask backend
  -> backend/universe.py   dynamic market-universe discovery
  -> backend/providers.py  Yahoo Finance market provider and RSS crawler
  -> backend/services.py   metric calculation, strategy selection, explainable scoring
  -> backend/app.py        REST API
```

## 本地开发

安装前端依赖：

```powershell
npm install
```

安装后端依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

启动后端：

```powershell
python -m backend.app
```

在第二个终端启动前端：

```powershell
npm run dev
```

打开 `http://127.0.0.1:5173`。

## 无代码市场扫描

主要用户流程是将选填股票字段留空。后端会在请求时发现候选股票，并把它们排序成投资研究想法：

- 美国：Yahoo Finance 预设筛选器，例如 most active 和 day gainers。
- 台湾：TWSE 开放数据，按成交金额排序。
- 新加坡：SGX securities API，按成交量排序。
- 中国 A 股和香港：来源可访问时使用 Eastmoney 动态市场列表；如果来源拒绝请求，则使用明确的备用 metadata。

API 响应包含 `scan.source`、`scan.requested`、`scan.succeeded`、`scan.failed` 和 `scan.discoveryErrors`，让 UI 可以显示扫描结果来自实时股票池探索还是备用数据。

## 选填股票代码格式

默认数据提供者遵循 Yahoo Finance 股票代码后缀：

- 美国：`AAPL`、`MSFT`、`NVDA`
- 中国 A 股：`600519.SS`、`300750.SZ`
- 香港：`0700.HK`、`9988.HK`
- 新加坡：`D05.SI`、`C38U.SI`
- 台湾：`2330.TW`、`2317.TW`

股票输入是选填的。只有在想把扫描范围缩小到已知公司时才需要使用，例如 `AAPL`、`0700.HK`、`D05.SI`、`2330.TW`、`600519.SS` 和 `300750.SZ`。

## 评分模型

评分设计刻意保持可解释：

- `momentum`：由实时历史收盘价计算近期价格趋势。
- `value`：由 trailing 或 forward PE 计算估值分数。
- `sentiment`：近期分市场新闻内容，按来源可信度、文章新鲜度、公司相关性、标题和 RSS 摘要加权。
- `risk`：beta 和实现波动率。
- `quality`：可取得时使用 ROE、利润率和负债权益比。

策略权重决定这些指标如何合并成最终分数。结果是研究辅助，不是财务建议。

## 测试

后端 API 测试使用依赖注入的假数据提供者，因此 CI 不需要依赖外部网络调用：

```powershell
python -m unittest discover backend/tests
```

前端 production build：

```powershell
npm run build
```

## Production 注意事项

- 扫描大型观察列表前，先加入缓存。第一版 production 使用 Redis 或 SQLite cache 就足够。
- 为每个外部数据源加入 rate limit 和 request timeout。
- 如需更高可靠性，请用付费市场数据 API 取代或补强 Yahoo Finance。
- 所有 API key 都应放在环境变量中，绝不要提交 `.env` 文件。
- 在完成身份验证、审计日志、合规审查和风控前，不要加入券商下单功能。

## 部署笔记

Linux 示例：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm ci
npm run build
gunicorn 'backend.app:app' --bind 127.0.0.1:8000
```

Windows 示例：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
npm install
npm run build
waitress-serve --listen=127.0.0.1:8000 backend.app:app
```

使用 Nginx、IIS 或其他 reverse proxy 服务 `dist/`，并把 `/api` 转发到 Flask service。

## 免责声明

本应用只提供投资研究流程辅助，不是财务建议，也不会执行交易。
