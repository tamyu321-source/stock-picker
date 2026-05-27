<p align="right">
  <a href="./README.md"><img src="https://flagcdn.com/w40/gb.png" alt="United Kingdom flag" width="22"> English</a> |
  <a href="./README.zh-TW.md"><img src="https://flagcdn.com/w40/tw.png" alt="Taiwan flag" width="22"> 繁體中文</a> |
  <a href="./README.nan-TW.md"><img src="https://flagcdn.com/w40/tw.png" alt="Taiwan flag" width="22"> 臺語</a> |
  <a href="./README.zh-CN.md"><img src="https://flagcdn.com/w40/cn.png" alt="China flag" width="22"> 简体中文</a>
</p>

# Open Stock Picker

Open Stock Picker 是一套支援多語系、以 AI 輔助的股票研究 Web App。主要流程是不需要寫程式的市場掃描：選擇市場與策略後，讓後端即時尋找、評分並排序較高品質、適合投資研究的股票，涵蓋中國、香港、新加坡、美國與臺灣。

它是為真實研究流程設計，不是靜態作品集展示。這個應用程式不會執行交易，也不會儲存券商帳號或憑證。

## 功能

- Vue 3 + Vite Web 介面，支援英文、簡體中文與繁體中文 UI。
- Python Flask 後端，整合即時資料來源與可解釋評分模型。
- 不需要先輸入股票代碼，就能直接掃描市場。
- 若使用者已經有特定股票，也可以選填股票代碼或公司名稱來縮小掃描範圍。
- 自動探索市場股票池，而不是依賴硬編碼清單。
- 透過 Yahoo Finance chart endpoints 取得即時價格歷史；若已安裝 `yfinance`，也可選擇使用。
- 透過 Google News 與在地來源篩選進行市場別 RSS/新聞爬取，並在可用時使用公司名稱與文章摘要。
- 內建平衡型、成長型與防禦價值型投資策略。
- 自訂策略滑桿，可調整動能、估值、情緒、風險與品質權重。
- 產生買入、觀察、賣出判斷，並附上決策理由與來源連結。

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

安裝前端相依套件：

```powershell
npm install
```

安裝後端相依套件：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

啟動後端：

```powershell
python -m backend.app
```

在第二個終端機啟動前端：

```powershell
npm run dev
```

開啟 `http://127.0.0.1:5173`。

## 免寫程式市場掃描

主要使用流程是將選填股票欄位留空。後端會在請求當下探索候選股票，並把它們排序成投資研究想法：

- 美國：Yahoo Finance 預設篩選器，例如 most active 與 day gainers。
- 臺灣：TWSE 開放資料，依成交金額排序。
- 新加坡：SGX securities API，依成交量排序。
- 中國 A 股與香港：來源可連線時使用 Eastmoney 動態市場清單；若來源拒絕請求，則使用明確的備援 metadata。

API 回應包含 `scan.source`、`scan.requested`、`scan.succeeded`、`scan.failed` 與 `scan.discoveryErrors`，讓 UI 可以顯示掃描結果來自即時股票池探索或備援資料。

## 選填股票代碼格式

預設資料提供者遵循 Yahoo Finance 股票代碼後綴：

- 美國：`AAPL`、`MSFT`、`NVDA`
- 中國 A 股：`600519.SS`、`300750.SZ`
- 香港：`0700.HK`、`9988.HK`
- 新加坡：`D05.SI`、`C38U.SI`
- 臺灣：`2330.TW`、`2317.TW`

股票輸入是選填的。只有在想把掃描範圍縮小到已知公司時才需要使用，例如 `AAPL`、`0700.HK`、`D05.SI`、`2330.TW`、`600519.SS` 與 `300750.SZ`。

## 評分模型

評分設計刻意保持可解釋：

- `momentum`：由即時歷史收盤價計算近期價格趨勢。
- `value`：由 trailing 或 forward PE 計算估值分數。
- `sentiment`：近期市場別新聞內容，依來源可信度、文章新鮮度、公司相關性、標題與 RSS 摘要加權。
- `risk`：beta 與實現波動率。
- `quality`：可取得時使用 ROE、利潤率與負債權益比。

策略權重決定這些指標如何合併成最終分數。結果是研究輔助，不是財務建議。

## 測試

後端 API 測試使用依賴注入的假資料提供者，因此 CI 不需要依賴外部網路呼叫：

```powershell
python -m unittest discover backend/tests
```

前端 production build：

```powershell
npm run build
```

## Production 注意事項

- 掃描大型觀察清單前，先加入快取。第一版 production 使用 Redis 或 SQLite cache 就足夠。
- 為每個外部資料來源加入 rate limit 與 request timeout。
- 若需要更高可靠性，請用付費市場資料 API 取代或補強 Yahoo Finance。
- 所有 API key 都應放在環境變數中，絕不要提交 `.env` 檔案。
- 在完成身份驗證、稽核紀錄、合規審查與風控前，不要加入券商下單功能。

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

使用 Nginx、IIS 或其他 reverse proxy 服務 `dist/`，並把 `/api` 轉發到 Flask service。

## 免責聲明

本應用程式只提供投資研究流程輔助，不是財務建議，也不會執行交易。
