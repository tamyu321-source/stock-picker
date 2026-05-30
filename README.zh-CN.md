<p align="right">
  <a href="./README.md"><img src="https://flagcdn.com/w40/gb.png" alt="United Kingdom flag" width="22"> English</a> |
  <a href="./README.zh-TW.md"><img src="https://flagcdn.com/w40/tw.png" alt="Taiwan flag" width="22"> 繁體中文</a> |
  <a href="./README.nan-TW.md"><img src="./assets/taiwan-green-island.svg" alt="Green Taiwan island flag" width="22"> 臺語</a> |
  <a href="./README.zh-CN.md"><img src="https://flagcdn.com/w40/cn.png" alt="China flag" width="22"> 简体中文</a>
</p>

# Open Stock Picker

[![CI](https://github.com/tamyu321-source/stock-picker/actions/workflows/ci.yml/badge.svg)](https://github.com/tamyu321-source/stock-picker/actions/workflows/ci.yml)
[![Deploy GitHub Pages](https://github.com/tamyu321-source/stock-picker/actions/workflows/deploy.yml/badge.svg)](https://github.com/tamyu321-source/stock-picker/actions/workflows/deploy.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)

Open Stock Picker 是一个多语言、AI 辅助的股票研究 Web App。它的主要流程是无代码市场扫描：选择市场和策略后，让 Python 后端实时发现、评分并排序更高质量、适合投资研究的股票，覆盖中国 A 股、香港、日本、韩国、新加坡、美国和台湾。

它面向真实研究流程设计，不是静态作品集展示。这个应用不会执行交易，也不会存储券商账号或凭证。

**在线预览：** [tamyu321-source.github.io/stock-picker](https://tamyu321-source.github.io/stock-picker/)

GitHub Pages 版本是静态演示模式，使用示例数据。要使用实时行情、RSS/新闻抓取和流式扫描，请在本地启动 Flask 后端。

![Open Stock Picker preview](./preview-stock-picker.png)

## 为什么值得使用

- 不需要先输入股票代码，就能直接扫描市场。
- 后端分析还在进行时，前端会逐步显示已经产生的候选股。
- 同一批评分结果可以同时查看个股和板块分析。
- 100 分制评分可拆解为动量、估值、新闻情绪、风险和质量。
- UI 支持英文、简体中文、繁体中文、台语、日文和韩文。
- 如果已经有特定标的，也可以用股票代码或公司名称缩小扫描范围。

## 功能

- Vue 3 + Vite Web 界面，支持设置保存和响应式研究工作区。
- Python Flask 后端，整合实时数据源、RSS/新闻抓取和可解释评分模型。
- 自动探索市场股票池，而不是依赖硬编码列表。
- 流式 NDJSON API，较长扫描中也能逐步显示结果。
- 通过 Yahoo Finance chart endpoints 获取价格历史；如果已安装 `yfinance`，也可以选择使用。
- 通过 Google News、Eastmoney fallback 和本地来源筛选进行分市场新闻抓取。
- 内置平衡型、成长型和防御价值型投资策略。
- 自定义策略滑杆，可调整动量、估值、情绪、风险和质量权重。
- 生成买入、观察、卖出判断，并附带决策理由、来源链接、操作方向和风控提醒。

## 市场覆盖

| 市场 | 代码示例 | 探索方式 |
| --- | --- | --- |
| 美国 | `AAPL`, `MSFT`, `NVDA` | Yahoo Finance 筛选器和新闻搜索 |
| 中国 A 股 | `600519.SS`, `300750.SZ` | Eastmoney 市场列表、本地名称和备用 metadata |
| 香港 | `0700.HK`, `9988.HK` | Eastmoney 港股列表和公司别名 |
| 日本 | `7203.T`, `6758.T` | 高流动性备用股票池和 Yahoo 代码 |
| 韩国 | `005930.KS`, `000660.KS` | 高流动性备用股票池和 Yahoo 代码 |
| 新加坡 | `D05.SI`, `C38U.SI` | SGX securities API，按成交量排序 |
| 台湾 | `2330.TW`, `2317.TW` | TWSE 开放数据、本地公司名称和 Yahoo/TWSE fallback |

## 架构

```text
Vue 3 web app
  -> /api/config          strategy, market, and default ticker metadata
  -> /api/analyze         live data fetch, RSS crawl, scoring, verdicts, explanations
  -> /api/analyze/stream  incremental NDJSON scan events

Flask backend
  -> backend/universe.py   dynamic market-universe discovery
  -> backend/providers.py  market data providers and RSS/news crawlers
  -> backend/services.py   metric calculation, strategy selection, explainable scoring
  -> backend/app.py        REST API
```

## 本地开发

```powershell
npm install
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m backend.app
```

在第二个终端启动前端：

```powershell
npm run dev
```

打开 `http://127.0.0.1:5173`。

## 静态演示与实时后端

- GitHub Pages 只服务 Vue 静态文件，因此使用内置示例数据，方便访客先看界面。
- 本地开发启动 `python -m backend.app` 后，才会使用实时 `/api/config`、`/api/analyze` 和 `/api/analyze/stream`。
- App 顶部会显示数据模式，让用户知道当前看到的是示例数据还是实时后端结果。

## 无代码市场扫描

主要用户流程是将选填股票字段留空。后端会在请求时发现候选股票，并把它们排序成投资研究想法。

空白扫描的探索顺序：

1. 本地财经新闻来源。
2. Google News 市场搜索。
3. Yahoo、Eastmoney、SGX、TWSE 等市场股票池 API。
4. 实时来源不可用时，使用高流动性备用列表。

API 响应包含 `scan.source`、`scan.requested`、`scan.succeeded`、`scan.displayed`、`scan.failed` 和 `scan.discoveryErrors`，让 UI 可以显示扫描结果来自实时探索、新闻驱动探索还是备用数据。

## 评分模型

- `momentum`：由历史收盘价计算近期价格趋势。
- `value`：由 trailing PE、forward PE、price-to-book 和可用替代指标计算估值分数。
- `sentiment`：近期分市场新闻内容，按来源可信度、文章新鲜度、公司相关性、标题和摘要加权。
- `risk`：beta、实现波动率和严重价格走弱检查。
- `quality`：可取得时使用 ROE、利润率、负债权益比、成长、规模和流动性。

策略权重决定这些指标如何合并成最终分数。结果是研究辅助，不是财务建议。

## 测试

```powershell
python -m unittest discover backend/tests
npm run build
```

Pull request 应通过 GitHub Actions 中的后端测试和前端 build。

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

## 参与贡献与安全

- [CONTRIBUTING.md](./CONTRIBUTING.md) 说明本地流程、验证命令和贡献范围。
- [SECURITY.md](./SECURITY.md) 说明报告方式和当前安全模型。

## 免责声明

本应用只提供投资研究流程辅助，不是财务建议，也不会执行交易。
