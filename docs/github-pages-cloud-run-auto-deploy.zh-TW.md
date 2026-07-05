# GitHub Pages + Cloud Run 自動部署

這份流程分成兩條部署線：

- GitHub Pages：由 `.github/workflows/deploy.yml` 部署前端。
- Cloud Run：由 `.github/workflows/deploy-cloud-run.yml` 部署 Flask API。

## 1. 本機先登入 Google Cloud

```powershell
gcloud auth login
gcloud config set project stock-picker-prod

gcloud services enable `
  run.googleapis.com `
  cloudbuild.googleapis.com `
  artifactregistry.googleapis.com `
  iamcredentials.googleapis.com
```

## 2. 建立 GitHub Actions 用的 Google Cloud 權限

PowerShell 執行：

```powershell
$PROJECT_ID = "stock-picker-prod"
$REGION = "asia-east1"
$REPO = "tamyu321-source/stock-picker"
$POOL_ID = "github-actions"
$PROVIDER_ID = "github"
$SA_ID = "github-cloud-run-deployer"
$SA_EMAIL = "$SA_ID@$PROJECT_ID.iam.gserviceaccount.com"
$PROJECT_NUMBER = gcloud projects describe $PROJECT_ID --format="value(projectNumber)"

gcloud iam service-accounts create $SA_ID `
  --project $PROJECT_ID `
  --display-name "GitHub Cloud Run Deployer"

gcloud projects add-iam-policy-binding $PROJECT_ID `
  --member "serviceAccount:$SA_EMAIL" `
  --role "roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID `
  --member "serviceAccount:$SA_EMAIL" `
  --role "roles/iam.serviceAccountUser"

gcloud projects add-iam-policy-binding $PROJECT_ID `
  --member "serviceAccount:$SA_EMAIL" `
  --role "roles/cloudbuild.builds.editor"

gcloud projects add-iam-policy-binding $PROJECT_ID `
  --member "serviceAccount:$SA_EMAIL" `
  --role "roles/artifactregistry.admin"
```

如果 service account 已存在，第一個 `create` 可能會報已存在；可以略過，繼續後面的 binding。

## 3. 建立 Workload Identity Federation

```powershell
gcloud iam workload-identity-pools create $POOL_ID `
  --project $PROJECT_ID `
  --location "global" `
  --display-name "GitHub Actions"

gcloud iam workload-identity-pools providers create-oidc $PROVIDER_ID `
  --project $PROJECT_ID `
  --location "global" `
  --workload-identity-pool $POOL_ID `
  --display-name "GitHub stock-picker" `
  --issuer-uri "https://token.actions.githubusercontent.com" `
  --attribute-mapping "google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.ref=assertion.ref" `
  --attribute-condition "assertion.repository=='tamyu321-source/stock-picker' && assertion.ref=='refs/heads/master'"

$WIF_PROVIDER = "projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL_ID/providers/$PROVIDER_ID"
$WIF_MEMBER = "principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL_ID/attribute.repository/$REPO"

gcloud iam service-accounts add-iam-policy-binding $SA_EMAIL `
  --project $PROJECT_ID `
  --role "roles/iam.workloadIdentityUser" `
  --member $WIF_MEMBER

Write-Host "GCP_WORKLOAD_IDENTITY_PROVIDER=$WIF_PROVIDER"
Write-Host "GCP_SERVICE_ACCOUNT=$SA_EMAIL"
```

## 4. 設定 GitHub Repository Variables

到 GitHub repository：

```text
Settings -> Secrets and variables -> Actions -> Variables -> New repository variable
```

先新增：

```text
GCP_WORKLOAD_IDENTITY_PROVIDER = 上一步輸出的 projects/.../providers/github
GCP_SERVICE_ACCOUNT = github-cloud-run-deployer@stock-picker-prod.iam.gserviceaccount.com
CLOUD_RUN_API_ACCESS_KEYS = 19940710
VITE_API_KEY = 19940710
```

也可以用 GitHub CLI：

```powershell
gh variable set GCP_WORKLOAD_IDENTITY_PROVIDER --body "$WIF_PROVIDER"
gh variable set GCP_SERVICE_ACCOUNT --body "$SA_EMAIL"
gh variable set CLOUD_RUN_API_ACCESS_KEYS --body "19940710"
gh variable set VITE_API_KEY --body "19940710"
```

## 5. 第一次部署 Cloud Run

把目前程式 push 到 `master` 後，Cloud Run workflow 會自動跑：

```text
Actions -> Deploy Cloud Run API
```

也可以在 GitHub Actions 頁面手動按：

```text
Deploy Cloud Run API -> Run workflow
```

部署成功後，到本機抓 Cloud Run URL：

```powershell
$API_URL = gcloud run services describe stock-picker-api `
  --region asia-east1 `
  --format "value(status.url)"

Write-Host $API_URL
```

測試 API：

```powershell
Invoke-RestMethod "$API_URL/api/health" `
  -Headers @{ "X-Stock-Picker-Key" = "19940710" }
```

## 6. 讓 GitHub Pages 指向 Cloud Run

把 Cloud Run URL 寫進 GitHub Repository Variable：

```powershell
gh variable set VITE_API_BASE_URL --body "$API_URL"
```

或到 GitHub UI 新增：

```text
VITE_API_BASE_URL = https://你的-cloud-run-url.a.run.app
```

不要在 URL 最後加 `/`。

## 7. 部署 GitHub Pages

到 GitHub Actions 手動跑一次：

```text
Deploy GitHub Pages -> Run workflow
```

之後每次 push 到 `master`：

- 前端會由 GitHub Pages workflow 更新。
- 後端相關檔案有變更時，Cloud Run workflow 會更新 API。

## 8. 控費建議

Cloud Run workflow 已設定：

```text
--max-instances=2
```

建議再到 Google Cloud Console 設 Billing budget alert，至少設定 50%、90%、100% 通知。
