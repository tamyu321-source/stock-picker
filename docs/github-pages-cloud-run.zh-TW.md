# GitHub Pages + Cloud Run 部署

這份文件假設 Google Cloud 專案已建立，專案 ID 是 `stock-picker-prod`。

## 1. 設定 Google Cloud CLI

先安裝 Google Cloud CLI，然後在 PowerShell 執行：

```powershell
gcloud auth login
gcloud config set project stock-picker-prod
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
```

## 2. 部署後端到 Cloud Run

如果想優先降低延遲，可使用台灣區域：

```powershell
gcloud run deploy stock-picker-api `
  --source . `
  --region asia-east1 `
  --allow-unauthenticated `
  --max-instances 2 `
  --set-env-vars ALLOWED_ORIGINS=https://tamyu321-source.github.io,API_ACCESS_KEYS=19940710
```

如果想優先貼近 Cloud Run 免費額度示例區域，可把 `--region asia-east1` 改成：

```powershell
--region us-central1
```

部署成功後，Google Cloud 會輸出一個 Service URL，例如：

```text
https://stock-picker-api-xxxxx-uc.a.run.app
```

測試 API：

```powershell
Invoke-RestMethod "https://stock-picker-api-xxxxx-uc.a.run.app/api/health"
```

API 會要求共享密鑰。測試時也可以明確帶上 header：

```powershell
Invoke-RestMethod "https://stock-picker-api-xxxxx-uc.a.run.app/api/health" `
  -Headers @{ "X-Stock-Picker-Key" = "19940710" }
```

## 3. 讓 GitHub Pages 使用 Cloud Run API

到 GitHub repository：

```text
Settings -> Secrets and variables -> Actions -> Variables -> New repository variable
```

新增：

```text
Name: VITE_API_BASE_URL
Value: https://stock-picker-api-xxxxx-uc.a.run.app
```

不要在 URL 最後加 `/`。

再新增一個 repository variable：

```text
Name: VITE_API_KEY
Value: 19940710
```

## 4. 重新部署 GitHub Pages

到 GitHub Actions 手動執行：

```text
Actions -> Deploy GitHub Pages -> Run workflow
```

或直接 push 到 `master`，workflow 會自動重新 build。

## 5. 驗證

打開：

```text
https://tamyu321-source.github.io/stock-picker/
```

瀏覽器 DevTools 的 Network 應該會看到請求打到 Cloud Run：

```text
https://stock-picker-api-xxxxx-uc.a.run.app/api/config
https://stock-picker-api-xxxxx-uc.a.run.app/api/analyze/stream
```

如果看到 CORS 錯誤，確認 Cloud Run 環境變數：

```powershell
gcloud run services update stock-picker-api `
  --region asia-east1 `
  --set-env-vars ALLOWED_ORIGINS=https://tamyu321-source.github.io,API_ACCESS_KEYS=19940710
```

如果你部署在 `us-central1`，上面的 `--region` 也要改成 `us-central1`。

## 成本設定建議

一開始保持 Cloud Run 預設的 `min instances = 0`，沒流量時可縮到 0。第一次請求可能會冷啟動，但小專案成本最低。
