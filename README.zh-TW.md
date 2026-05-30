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

Open Stock Picker 是一套支援多語系、以 AI 輔助的股票研究 Web App。主要流程是不需要寫程式的市場掃描：選擇市場與策略後，讓 Python 後端即時尋找、評分並排序較高品質、適合投資研究的股票，涵蓋中國 A 股、香港、日本、韓國、新加坡、美國與臺灣。

它是為真實研究流程設計，不是靜態作品集展示。這個應用程式不會執行交易，也不會儲存券商帳號或憑證。

**線上預覽：** [tamyu321-source.github.io/stock-picker](https://tamyu321-source.github.io/stock-picker/)

GitHub Pages 版本是靜態示範模式，使用範例資料。若要使用即時行情、RSS/新聞爬取與串流掃描，請在本機啟動 Flask 後端。

![Open Stock Picker preview](./preview-stock-picker.png)

## 為什麼值得使用

- 不需要先輸入股票代碼，就能直接掃描市場。
- 後端分析還在進行時，前端會逐步顯示已產生的候選股。
- 較長掃描可隨時取消，已串流出來的候選股會保留。
- 同一批評分結果可同時查看個股與板塊分析。
- 可在本機保存最近掃描，並匯出 Markdown 或 JSON 研究筆記。
- 100 分制評分可拆解為動能、估值、新聞情緒、風險與品質。
- UI 支援英文、簡體中文、繁體中文、臺語、日文與韓文。
- 若已經有特定標的，也可用股票代碼或公司名稱縮小掃描範圍。

## 功能

- Vue 3 + Vite Web 介面，支援設定保存與響應式研究工作區。
- Python Flask 後端，整合即時資料來源、RSS/新聞爬取與可解釋評分模型。
- 自動探索市場股票池，而不是依賴硬編碼清單。
- 串流 NDJSON API，較長掃描中也能逐步顯示結果。
- 透過瀏覽器 `AbortController` 支援取消掃描請求。
- 共享短期記憶體 TTL cache，降低重複行情與新聞請求。
- 本機保存掃描紀錄，並支援 Markdown 與 JSON 匯出，方便後續研究。
- 透過 Yahoo Finance chart endpoints 取得價格歷史；若已安裝 `yfinance`，也可選擇使用。
- 透過 Google News、Eastmoney fallback 與在地來源篩選進行市場別新聞爬取。
- 內建平衡型、成長型與防禦價值型投資策略。
- 自訂策略滑桿，可調整動能、估值、情緒、風險與品質權重。
- 產生買入、觀察、賣出判斷，並附上決策理由、來源連結、操作方向與風控提醒。

## 市場涵蓋

| 市場 | 代碼範例 | 探索方式 |
| --- | --- | --- |
| 美國 | `AAPL`, `MSFT`, `NVDA` | Yahoo Finance 篩選器與新聞搜尋 |
| 中國 A 股 | `600519.SS`, `300750.SZ` | Eastmoney 市場清單、在地名稱與備援 metadata |
| 香港 | `0700.HK`, `9988.HK` | Eastmoney 港股清單與公司別名 |
| 日本 | `7203.T`, `6758.T` | 高流動性備援股票池與 Yahoo 代碼 |
| 韓國 | `005930.KS`, `000660.KS` | 高流動性備援股票池與 Yahoo 代碼 |
| 新加坡 | `D05.SI`, `C38U.SI` | SGX securities API，依成交量排序 |
| 臺灣 | `2330.TW`, `2317.TW` | TWSE 開放資料、在地公司名稱與 Yahoo/TWSE fallback |

## 架構

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

## 本機開發

```powershell
npm install
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m backend.app
```

在第二個終端機啟動前端：

```powershell
npm run dev
```

開啟 `http://127.0.0.1:5173`。

## 靜態示範與即時後端

- GitHub Pages 只服務 Vue 靜態檔，因此使用內建範例資料，方便訪客先看介面。
- 本機開發啟動 `python -m backend.app` 後，才會使用即時 `/api/config`、`/api/analyze` 與 `/api/analyze/stream`。
- App 頂部會顯示資料模式，讓使用者知道目前看到的是範例資料或即時後端結果。

## 免寫程式市場掃描

主要使用流程是將選填股票欄位留空。後端會在請求當下探索候選股票，並把它們排序成投資研究想法。

空白掃描的探索順序：

1. 在地財經新聞來源。
2. Google News 市場搜尋。
3. Yahoo、Eastmoney、SGX、TWSE 等市場股票池 API。
4. 即時來源不可用時，使用高流動性備援清單。

API 回應包含 `scan.source`、`scan.requested`、`scan.succeeded`、`scan.displayed`、`scan.failed` 與 `scan.discoveryErrors`，讓 UI 可以顯示掃描結果來自即時探索、新聞驅動探索或備援資料。

## 評分模型

- `momentum`：由歷史收盤價計算近期價格趨勢。
- `value`：由 trailing PE、forward PE、price-to-book 與可用替代指標計算估值分數。
- `sentiment`：近期市場別新聞內容，依來源可信度、文章新鮮度、公司相關性、標題與摘要加權。
- `risk`：beta、實現波動率與嚴重價格走弱檢查。
- `quality`：可取得時使用 ROE、利潤率、負債權益比、成長、規模與流動性。

策略權重決定這些指標如何合併成最終分數。結果是研究輔助，不是財務建議。

## 測試

```powershell
python -m unittest discover backend/tests
npm run build
```

Pull request 應通過 GitHub Actions 中的後端測試與前端 build。

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

## 參與貢獻與安全

- [CONTRIBUTING.md](./CONTRIBUTING.md) 說明本機流程、驗證命令與貢獻範圍。
- [SECURITY.md](./SECURITY.md) 說明回報方式與目前安全模型。

## 免責聲明

本應用程式只提供投資研究流程輔助，不是財務建議，也不會執行交易。
