<p align="right">
  <a href="./README.md"><img src="https://flagcdn.com/w40/gb.png" alt="United Kingdom flag" width="22"> English</a> |
  <a href="./README.zh-TW.md"><img src="https://flagcdn.com/w40/tw.png" alt="Taiwan flag" width="22"> 繁體中文</a> |
  <a href="./README.nan-TW.md"><img src="./assets/taiwan-green-island.svg" alt="Green Taiwan island flag" width="22"> 臺語（ㄉㄞˊ ㄍㄧˋ）</a> |
  <a href="./README.zh-CN.md"><img src="https://flagcdn.com/w40/cn.png" alt="China flag" width="22"> 简体中文</a>
</p>

# Open Stock Picker

Open Stock Picker is a multilingual AI-assisted stock research web app. Its primary workflow is no-code market scanning: choose markets and a strategy, then let the backend discover, score, and rank suitable higher-quality stocks for investment research across China, Hong Kong, Singapore, the United States, and Taiwan.

It is designed for real research workflows, not a static portfolio mockup. The app does not execute trades and does not store broker credentials.

## Features

- Vue 3 + Vite web interface with English, Simplified Chinese, and Traditional Chinese UI.
- Python Flask backend with live data providers and explainable scoring.
- Direct market scanning without requiring users to enter stock codes first.
- Optional ticker or company-name input for narrowing a scan when the user already has a specific stock in mind.
- Automatic market-universe discovery instead of a hard-coded stock list.
- Live price history through Yahoo Finance chart endpoints, with optional `yfinance` support when installed.
- Market-specific RSS/news crawling through Google News and local source filters, using company names and article summaries when available.
- Default strategies for balanced, growth, and defensive value investing.
- Custom strategy sliders for momentum, valuation, sentiment, risk, and quality weights.
- Buy, watch, and sell verdicts with decision reasons and source links.

## Architecture

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

## No-Code Market Scan

The main user flow is to leave the optional stock field empty. The backend then discovers candidates at request time and ranks them as investment research ideas:

- United States: Yahoo Finance predefined screeners such as most active and day gainers.
- Taiwan: TWSE open data sorted by trading value.
- Singapore: SGX securities API sorted by trading volume.
- China A-shares and Hong Kong: Eastmoney dynamic market lists when reachable, with explicit fallback metadata if the source refuses the request.

The API response includes `scan.source`, `scan.requested`, `scan.succeeded`, `scan.failed`, and `scan.discoveryErrors` so the UI can show whether a scan came from live universe discovery or a fallback.

## Optional Ticker Format

The default provider follows Yahoo Finance ticker suffixes:

- United States: `AAPL`, `MSFT`, `NVDA`
- China A-shares: `600519.SS`, `300750.SZ`
- Hong Kong: `0700.HK`, `9988.HK`
- Singapore: `D05.SI`, `C38U.SI`
- Taiwan: `2330.TW`, `2317.TW`

Ticker input is optional. Use it only to narrow a scan to known companies such as `AAPL`, `0700.HK`, `D05.SI`, `2330.TW`, `600519.SS`, and `300750.SZ`.

## Scoring Model

The score is intentionally explainable:

- `momentum`: recent price trend from live historical closes.
- `value`: valuation score from trailing or forward PE.
- `sentiment`: recent market-specific news content, weighted by source credibility, article recency, company relevance, title, and RSS summary.
- `risk`: beta and realized volatility.
- `quality`: ROE, profit margin, and debt-to-equity when available.

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

## Production Notes

- Add caching before scanning large watchlists. A Redis or SQLite cache is enough for a first production version.
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

## Disclaimer

This application is for investment research workflow support only. It is not financial advice and does not execute trades.
