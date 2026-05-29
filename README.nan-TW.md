<p align="right">
  <a href="./README.md"><img src="https://flagcdn.com/w40/gb.png" alt="United Kingdom flag" width="22"> English</a> |
  <a href="./README.zh-TW.md"><img src="https://flagcdn.com/w40/tw.png" alt="Taiwan flag" width="22"> 繁體中文</a> |
  <a href="./README.nan-TW.md"><img src="./assets/taiwan-green-island.svg" alt="Green Taiwan island flag" width="22"> 臺語</a> |
  <a href="./README.zh-CN.md"><img src="https://flagcdn.com/w40/cn.png" alt="China flag" width="22"> 简体中文</a>
</p>

# Open Stock Picker

Open Stock Picker 是一套用 AI 幫咱做股票研究的 Web App。主要流程是免寫程式的市場掃描：揀好市場佮策略了後，後端會即時去揣股票、評分、照分數排序，幫咱整理較有品質、適合投資研究的候選股，範圍包含中國、香港、新加坡、美國佮臺灣。

這个 app 是照實際研究流程設計，毋是靜態作品集展示。它袂執行交易，嘛袂保存券商帳號抑是憑證。

## 臺語版用字

這份 README 用臺灣閩南語常見漢字佮白話語氣，技術名詞保留英文或通用寫法，予內容較好讀。若遇著無好寫的語氣，才用注音符號；這版先以漢字為主，避免變做整段注音。

## 功能

- Vue 3 + Vite Web 介面，支援英文、簡體中文、繁體中文佮臺語版 UI。
- Python Flask 後端，串接即時資料來源佮會使解說的評分模型。
- 毋免先輸入股票代號，就會使直接掃市場。
- 若使用者已經有指定股票，嘛會使選填股票代號抑是公司名，予掃描範圍較精準。
- 自動揣市場股票池，毋是靠寫死的股票清單。
- 透過 Yahoo Finance chart endpoints 取得即時價位歷史；若有安裝 `yfinance`，嘛會使選擇使用。
- 透過 Google News 佮在地來源篩選，做市場別 RSS / 新聞爬取；有資料時會使用公司名佮文章摘要。
- 內建平衡型、成長型佮防禦價值型投資策略。
- 家己調策略滑桿，會使調整 momentum、valuation、sentiment、risk 佮 quality 權重。
- 產生買入、觀察、退出風險判斷，閣附決策理由佮來源連結。

## 架構

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

## 本機開發

安裝 frontend 相依套件：

```powershell
npm install
```

安裝 backend 相依套件：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

啟動 backend：

```powershell
python -m backend.app
```

佇第二个 terminal 啟動 frontend：

```powershell
npm run dev
```

開 `http://127.0.0.1:5173`。

## 免寫程式的市場掃描

主要使用方式是共選填股票欄位留空。Backend 會佇 request 的時陣揣候選股票，閣照分數排做投資研究想法：

- 美國：Yahoo Finance 預設篩選器，親像 most active 佮 day gainers。
- 臺灣：TWSE open data，照成交金額排序。
- 新加坡：SGX securities API，照成交量排序。
- 中國 A 股佮香港：若連線有通，使用 Eastmoney 動態市場清單；若來源擋 request，就用明確的 fallback metadata。

API 回應有 `scan.source`、`scan.requested`、`scan.succeeded`、`scan.failed` 佮 `scan.discoveryErrors`，予 UI 會使顯示掃描是來自即時股票池探索，抑是 fallback 資料。

## 選填股票代號格式

預設資料提供者照 Yahoo Finance 股票代號 suffix：

- 美國：`AAPL`、`MSFT`、`NVDA`
- 中國 A 股：`600519.SS`、`300750.SZ`
- 香港：`0700.HK`、`9988.HK`
- 新加坡：`D05.SI`、`C38U.SI`
- 臺灣：`2330.TW`、`2317.TW`

股票輸入是選填的。只有想欲共掃描範圍縮到已知公司時才需要用，親像 `AAPL`、`0700.HK`、`D05.SI`、`2330.TW`、`600519.SS` 佮 `300750.SZ`。

## 評分模型

評分設計故意保持會使解說：

- `momentum`：用即時歷史收盤價算近期價位趨勢。
- `value`：用 trailing 抑是 forward PE 算 valuation score。
- `sentiment`：近期市場別新聞內容，照來源可信度、文章新鮮度、公司相關性、標題佮 RSS 摘要加權。
- `risk`：beta 佮 realized volatility。
- `quality`：若資料有，使用 ROE、profit margin 佮 debt-to-equity。

策略權重決定遮的指標按怎合做最後分數。結果是研究輔助，毋是財務建議。

## 測試

Backend API 測試使用 dependency-injected fake providers，所以 CI 毋免靠外部網路呼叫：

```powershell
python -m unittest discover backend/tests
```

Frontend production build：

```powershell
npm run build
```

## Production 注意事項

- 掃描大型 watchlist 進前，先加 cache。第一版 production 用 Redis 抑是 SQLite cache 就夠。
- 替每个外部資料來源加 rate limit 佮 request timeout。
- 若需要較高可靠性，用付費 market-data API 取代抑是補強 Yahoo Finance。
- 所有 API key 攏愛放佇環境變數，毋通提交 `.env` 檔案。
- 佇完成身份驗證、稽核紀錄、合規審查佮風控進前，毋通加入券商下單功能。

## 部署筆記

Linux 範例：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
npm ci
npm run build
gunicorn 'backend.app:app' --bind 127.0.0.1:8000
```

Windows 範例：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
npm install
npm run build
waitress-serve --listen=127.0.0.1:8000 backend.app:app
```

用 Nginx、IIS 抑是其他 reverse proxy 服務 `dist/`，閣共 `/api` 轉送去 Flask service。

## 免責聲明

這个 app 只提供投資研究流程輔助，毋是財務建議，嘛袂執行交易。
