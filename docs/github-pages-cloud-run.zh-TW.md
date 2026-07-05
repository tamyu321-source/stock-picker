# GitHub Pages + Cloud Run 部署

這份文件說明如何把前端部署到 GitHub Pages，並把 Flask API 部署到 Google Cloud Run。

目前假設：

- Google Cloud 專案 ID：`stock-picker-prod`
- Cloud Run 服務名稱：`stock-picker-api`
- Cloud Run 區域：`asia-east1`
- GitHub Pages 網址：`https://tamyu321-source.github.io/stock-picker/`
- API 共享密鑰：`19940710`

## 1. 如果你在 Google Cloud Shell

Cloud Shell 是 bash。換行請用反斜線 `\`，不要用 PowerShell 的反引號。

Cloud Shell 已經登入 Google，不需要再跑 `gcloud auth login`。

```bash
gcloud config set project stock-picker-prod

gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  iamcredentials.googleapis.com
```

## 2. 如果你在 Windows PowerShell

PowerShell 才使用反引號續行：

```powershell
gcloud auth login
gcloud config set project stock-picker-prod

gcloud services enable `
  run.googleapis.com `
  cloudbuild.googleapis.com `
  artifactregistry.googleapis.com `
  iamcredentials.googleapis.com
```

## 3. 手動部署 Cloud Run API

在 Cloud Shell/bash 使用：

```bash
gcloud run deploy stock-picker-api \
  --source . \
  --region asia-east1 \
  --allow-unauthenticated \
  --max-instances 2 \
  --set-env-vars ALLOWED_ORIGINS=https://tamyu321-source.github.io,API_ACCESS_KEYS=19940710
```

在 Windows PowerShell 使用：

```powershell
gcloud run deploy stock-picker-api `
  --source . `
  --region asia-east1 `
  --allow-unauthenticated `
  --max-instances 2 `
  --set-env-vars ALLOWED_ORIGINS=https://tamyu321-source.github.io,API_ACCESS_KEYS=19940710
```

說明：

- `--allow-unauthenticated` 讓瀏覽器可以連到 Cloud Run。
- 後端仍會檢查 `X-Stock-Picker-Key: 19940710`。
- `--max-instances 2` 用來限制最高擴張數量，降低被刷爆費用的風險。

## 4. 取得並測試 Cloud Run URL

Cloud Shell/bash：

```bash
API_URL="$(gcloud run services describe stock-picker-api \
  --region asia-east1 \
  --format "value(status.url)")"

echo "$API_URL"

curl -H "X-Stock-Picker-Key: 19940710" "$API_URL/api/health"
```

Windows PowerShell：

```powershell
$API_URL = gcloud run services describe stock-picker-api `
  --region asia-east1 `
  --format "value(status.url)"

Write-Host $API_URL

Invoke-RestMethod "$API_URL/api/health" `
  -Headers @{ "X-Stock-Picker-Key" = "19940710" }
```

成功時應該會看到類似：

```json
{
  "service": "open-stock-picker",
  "status": "ok"
}
```

## 5. 設定 GitHub Pages 使用 Cloud Run API

到 GitHub repository：

```text
Settings -> Secrets and variables -> Actions -> Variables -> New repository variable
```

新增：

```text
VITE_API_BASE_URL = https://你的-cloud-run-url.a.run.app
VITE_API_KEY = 19940710
```

注意：

- `VITE_API_BASE_URL` 最後不要加 `/`。
- `VITE_API_KEY` 會被打包到 GitHub Pages 前端，所以它只是共享門禁，不是真正私密密鑰。

如果你有 GitHub CLI，也可以用：

```bash
gh variable set VITE_API_BASE_URL --body "$API_URL"
gh variable set VITE_API_KEY --body "19940710"
```

## 6. 部署 GitHub Pages

到 GitHub Actions 手動執行：

```text
Actions -> Deploy GitHub Pages -> Run workflow
```

或直接 push 到 `master`，Pages workflow 會自動重新 build。

## 7. 驗證網站

打開：

```text
https://tamyu321-source.github.io/stock-picker/
```

瀏覽器 DevTools 的 Network 應該會看到請求打到 Cloud Run：

```text
https://你的-cloud-run-url.a.run.app/api/config
https://你的-cloud-run-url.a.run.app/api/analyze/stream
```

如果看到 CORS 錯誤，重新設定 Cloud Run 環境變數：

Cloud Shell/bash：

```bash
gcloud run services update stock-picker-api \
  --region asia-east1 \
  --set-env-vars ALLOWED_ORIGINS=https://tamyu321-source.github.io,API_ACCESS_KEYS=19940710
```

PowerShell：

```powershell
gcloud run services update stock-picker-api `
  --region asia-east1 `
  --set-env-vars ALLOWED_ORIGINS=https://tamyu321-source.github.io,API_ACCESS_KEYS=19940710
```

## 8. 成本建議

一開始保持：

- `min instances = 0`
- `max instances = 2`

另外建議到 Google Cloud Console 設定 Billing budget alert，例如 50%、90%、100% 通知。
