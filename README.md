<p align="right">
  <a href="./README.md"><img src="https://flagcdn.com/w40/gb.png" alt="United Kingdom flag" width="22"> English</a> |
  <a href="./README.zh-TW.md"><img src="https://flagcdn.com/w40/tw.png" alt="Taiwan flag" width="22"> 繁體中文</a> |
  <a href="./README.nan-TW.md"><img src="./assets/taiwan-green-island.svg" alt="Green Taiwan island flag" width="22"> 臺語</a> |
  <a href="./README.zh-CN.md"><img src="https://flagcdn.com/w40/cn.png" alt="China flag" width="22"> 简体中文</a> |
  <a href="./README.ja.md"><img src="https://flagcdn.com/w40/jp.png" alt="Japan flag" width="22"> 日本語</a> |
  <a href="./README.ko.md"><img src="https://flagcdn.com/w40/kr.png" alt="South Korea flag" width="22"> 한국어</a>
</p>

# Open Stock Picker

[![CI](https://github.com/tamyu321-source/stock-picker/actions/workflows/ci.yml/badge.svg)](https://github.com/tamyu321-source/stock-picker/actions/workflows/ci.yml)
[![Deploy GitHub Pages](https://github.com/tamyu321-source/stock-picker/actions/workflows/deploy.yml/badge.svg)](https://github.com/tamyu321-source/stock-picker/actions/workflows/deploy.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)

Open Stock Picker is a multilingual AI-assisted stock research web app. Its main workflow is no-code market scanning: choose markets and a strategy, then let the Python backend discover, score, and rank higher-quality stocks for investment research across China A-shares, Hong Kong, Japan, South Korea, Singapore, the United States, and Taiwan.

It is designed for real research workflows, not a static portfolio mockup. The app does not execute trades and does not store broker credentials.

**Hosted preview:** [tamyu321-source.github.io/stock-picker](https://tamyu321-source.github.io/stock-picker/)

The hosted GitHub Pages build runs in static demo mode with sample data. Run the Flask backend locally to use live market data, RSS/news crawling, and streaming scans.

![Open Stock Picker preview](./preview-stock-picker.png)

## Why It Is Useful

- Scan markets directly without entering tickers first.
- See live, incremental picks while the backend is still analyzing.
- Cancel longer scans without losing any picks that already streamed in.
- Compare stock-level and sector-level results from the same scored candidate set.
- Save recent scans locally and export research notes as Markdown or JSON.
- Inspect explainable 100-point scoring across momentum, value, news sentiment, risk, and quality.
- Use English, Simplified Chinese, Traditional Chinese, Taiwanese, Japanese, or Korean UI.
- Narrow a scan with ticker or company-name input when you already know what to research.

## Features

- Vue 3 + Vite frontend with persistent settings and responsive research workspace.
- Python Flask backend with live data providers, RSS/news crawling, and explainable scoring.
- Direct market scanning without requiring users to enter stock codes first.
- Automatic market-universe discovery instead of a hard-coded stock list.
- Streaming NDJSON API so picks appear progressively during longer scans.
- Cancellable scan requests wired through browser `AbortController`.
- Shared in-memory TTL cache for repeated market-data and news requests.
- Local saved-scan history plus Markdown and JSON export for follow-up research.
- Live price history through Yahoo Finance chart endpoints, with optional `yfinance` support when installed.
- Market-specific RSS/news crawling through Google News, Eastmoney fallbacks, and local source filters.
- Default strategies for balanced, growth, and defensive value investing.
- Custom strategy sliders for momentum, valuation, sentiment, risk, and quality weights.
- Buy, watch, and sell verdicts with decision reasons, source links, action plans, and risk controls.

## Market Coverage

| Market | Ticker examples | Discovery notes |
| --- | --- | --- |
| United States | `AAPL`, `MSFT`, `NVDA` | Yahoo Finance screeners and news search |
| China A-shares | `600519.SS`, `300750.SZ` | Eastmoney market lists, local names, and fallback metadata |
| Hong Kong | `0700.HK`, `9988.HK` | Eastmoney Hong Kong lists and company aliases |
| Japan | `7203.T`, `6758.T` | Curated liquid universe plus Yahoo-style symbols |
| South Korea | `005930.KS`, `000660.KS` | Curated liquid universe plus Yahoo-style symbols |
| Singapore | `D05.SI`, `C38U.SI` | SGX securities API sorted by volume |
| Taiwan | `2330.TW`, `2317.TW` | TWSE open data, local company names, and Yahoo/TWSE fallback |

## Architecture

```text
Vue 3 web app
  -> /api/config          strategy, market, and default ticker metadata
  -> /api/analyze         live data fetch, RSS crawl, scoring, verdicts, explanations
  -> /api/analyze/stream  incremental NDJSON scan events

Flask backend
  -> backend/universe.py   dynamic market-universe discovery
  -> backend/providers.py  market data providers and RSS/news crawlers
  -> backend/cache.py      short-lived in-memory cache for repeated provider calls
  -> backend/services.py   metric calculation, strategy selection, explainable scoring
  -> backend/app.py        REST API
```

## Local Development

Install frontend dependencies:

```powershell
npm install
```

Install backend dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Run the backend:

```powershell
python -m backend.app
```

Run the frontend in a second terminal:

```powershell
npm run dev
```

Open `http://127.0.0.1:5173`.

## Static Demo vs Live Backend

- GitHub Pages serves the Vue build only. It uses built-in sample data so visitors can inspect the interface without running Python.
- Local development with `python -m backend.app` enables live `/api/config`, `/api/analyze`, and `/api/analyze/stream`.
- The app shows a data-mode status in the top strip so users can tell whether they are looking at sample data or live backend output.

## No-Code Market Scan

The main user flow is to leave the optional stock field empty. The backend then discovers candidates at request time and ranks them as investment research ideas.

Discovery priority for blank scans:

1. Local finance-news sources.
2. Google News market searches.
3. Market-universe APIs such as Yahoo, Eastmoney, SGX, and TWSE.
4. Curated fallback symbols when live sources are unreachable.

The API response includes `scan.source`, `scan.requested`, `scan.succeeded`, `scan.displayed`, `scan.failed`, and `scan.discoveryErrors` so the UI can show whether a scan came from live universe discovery, news-led discovery, or a fallback.

## Scoring Model

The score is intentionally explainable:

- `momentum`: recent price trend from live historical closes.
- `value`: valuation score from trailing PE, forward PE, price-to-book, and available proxy metrics.
- `sentiment`: recent market-specific news content, weighted by source credibility, article recency, company relevance, title, and RSS summary.
- `risk`: beta, realized volatility, and severe price-action checks.
- `quality`: ROE, profit margin, debt-to-equity, growth, size, and liquidity when available.

The strategy weights determine how these metrics combine into a final score. The result is research support, not financial advice.

## Testing

Backend API tests use dependency-injected fake providers so CI does not depend on external network calls:

```powershell
python -m unittest discover backend/tests
```

Frontend production build:

```powershell
npm run build
```

Pull requests are expected to pass both checks in GitHub Actions.

## Production Notes

- Add caching before scanning large watchlists. A Redis or SQLite cache is enough for a first production version.
- The default Flask app already includes a short-lived in-memory cache for repeated scans in one process.
- Add rate limits and request timeouts for every external provider.
- For higher reliability, replace or supplement Yahoo Finance with a paid market-data API.
- Keep all API keys in environment variables and never commit `.env` files.
- Do not add broker order placement until authentication, audit logs, compliance review, and risk controls are built.

## Deployment Notes

Linux example:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm ci
npm run build
gunicorn 'backend.app:app' --bind 127.0.0.1:8000
```

Windows example:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
npm install
npm run build
waitress-serve --listen=127.0.0.1:8000 backend.app:app
```

Use Nginx, IIS, or another reverse proxy to serve `dist/` and forward `/api` to the Flask service.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md) for the local workflow, validation commands, and contribution scope.

## Security

See [SECURITY.md](./SECURITY.md) for reporting guidance and the current security model.

## Disclaimer

This application is for investment research workflow support only. It is not financial advice and does not execute trades.
