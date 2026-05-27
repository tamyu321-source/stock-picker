<p align="right">
  <a href="./README.md"><img src="https://flagcdn.com/w40/gb.png" alt="United Kingdom flag" width="22"> English</a> |
  <a href="./README.zh-TW.md"><img src="https://flagcdn.com/w40/tw.png" alt="Taiwan flag" width="22"> 繁體中文</a> |
  <a href="./README.nan-TW.md"><img src="https://flagcdn.com/w40/tw.png" alt="Taiwan flag" width="22"> 臺語</a> |
  <a href="./README.zh-CN.md"><img src="https://flagcdn.com/w40/cn.png" alt="China flag" width="22"> 简体中文</a>
</p>

# Open Stock Picker

Open Stock Picker 是一套有 AI 鬥相共 ê 股票研究 Web App。主要 ê 流程是免寫 code ê 市場掃描：揀市場 kap 策略了後，予 backend 即時去揣、評分、排序較有品質 ê 股票，做投資研究 ê 參考，範圍包含中國、香港、新加坡、美國 kap 臺灣。

這个 app 是為著實際研究流程來設計，毋是靜態作品集。伊袂執行交易，嘛袂保存券商帳號抑是憑證。

## 功能

- Vue 3 + Vite Web 介面，支援英文、簡體中文 kap 繁體中文 UI。
- Python Flask backend，接即時資料來源 kap ē-sái 解說 ê 評分模型。
- 毋免先輸入股票代碼，就 ē-sái 直接掃描市場。
- 若使用者已經有特定股票，嘛 ē-sái 選填股票代碼抑是公司名，予掃描範圍較細。
- 自動揣市場股票池，毋是靠寫死 ê 股票清單。
- 透過 Yahoo Finance chart endpoints 取得即時價位歷史；若有安裝 `yfinance`，嘛 ē-sái 選擇使用。
- 透過 Google News kap 在地來源篩選，做市場別 RSS/新聞爬取；有資料 ê 時陣，會用公司名 kap 文章摘要。
- 內建平衡型、成長型 kap 防禦價值型投資策略。
- 自訂策略滑桿，ē-sái 調整 momentum、valuation、sentiment、risk kap quality 權重。
- 產生買入、觀察、賣出判斷，閣附決策理由 kap 來源連結。

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

## 免寫 code ê 市場掃描

主要使用流程是 kā 選填股票欄位留空。Backend 會佇 request ê 時陣揣候選股票，閣 kā 排做投資研究想法：

- 美國：Yahoo Finance 預設篩選器，親像 most active kap day gainers。
- 臺灣：TWSE open data，照成交金額排序。
- 新加坡：SGX securities API，照成交量排序。
- 中國 A 股 kap 香港：若連線有通，使用 Eastmoney 動態市場清單；若來源拒絕 request，就用明確 ê fallback metadata。

API 回應有 `scan.source`、`scan.requested`、`scan.succeeded`、`scan.failed` kap `scan.discoveryErrors`，予 UI ē-sái 顯示掃描是來自即時股票池探索，抑是 fallback 資料。

## 選填股票代碼格式

預設資料提供者照 Yahoo Finance 股票代碼 suffix：

- 美國：`AAPL`、`MSFT`、`NVDA`
- 中國 A 股：`600519.SS`、`300750.SZ`
- 香港：`0700.HK`、`9988.HK`
- 新加坡：`D05.SI`、`C38U.SI`
- 臺灣：`2330.TW`、`2317.TW`

股票輸入是選填 ê。只有想欲 kā 掃描範圍縮到已知公司 ê 時陣才需要用，親像 `AAPL`、`0700.HK`、`D05.SI`、`2330.TW`、`600519.SS` kap `300750.SZ`。

## 評分模型

評分設計是故意保持 ē-sái 解說：

- `momentum`：用即時歷史收盤價算近期價位趨勢。
- `value`：用 trailing 抑是 forward PE 算 valuation score。
- `sentiment`：近期市場別新聞內容，照來源可信度、文章新鮮度、公司相關性、標題 kap RSS 摘要加權。
- `risk`：beta kap realized volatility。
- `quality`：若資料有，使用 ROE、profit margin kap debt-to-equity。

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
- 替每个外部資料來源加 rate limit kap request timeout。
- 若需要較高可靠性，用付費 market-data API 取代抑是補強 Yahoo Finance。
- 所有 API key 攏愛囥佇環境變數，毋通提交 `.env` 檔案。
- 佇完成身份驗證、稽核紀錄、合規審查 kap 風控進前，毋通加入券商落單功能。

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

用 Nginx、IIS 抑是其他 reverse proxy 服務 `dist/`，閣 kā `/api` 轉送去 Flask service。

## 免責聲明

這个 app 只有提供投資研究流程輔助，毋是財務建議，嘛袂執行交易。
