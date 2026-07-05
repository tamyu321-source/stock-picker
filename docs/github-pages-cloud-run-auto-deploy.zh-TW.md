# GitHub Pages + Cloud Run 自動部署

這份文件說明如何設定「push 到 GitHub 後自動更新 Cloud Run API」。

部署線分成兩條：

- GitHub Pages：`.github/workflows/deploy.yml` 部署 Vue 前端。
- Cloud Run：`.github/workflows/deploy-cloud-run.yml` 部署 Flask API。

建議在 Google Cloud Shell 執行下面命令。Cloud Shell 是 bash，所以換行使用 `\`。

## 1. 確認 Google Cloud 專案

Cloud Shell 已經登入 Google，不需要再執行 `gcloud auth login`。

```bash
gcloud config set project stock-picker-prod
gcloud config get-value project
```

應該看到：

```text
stock-picker-prod
```

## 2. 啟用必要 API

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  iamcredentials.googleapis.com
```

## 3. 建立 GitHub Actions 用的 Service Account

```bash
PROJECT_ID="stock-picker-prod"
REGION="asia-east1"
REPO="tamyu321-source/stock-picker"
POOL_ID="github-actions"
PROVIDER_ID="github"
SA_ID="github-cloud-run-deployer"
SA_EMAIL="${SA_ID}@${PROJECT_ID}.iam.gserviceaccount.com"
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")"

gcloud iam service-accounts create "$SA_ID" \
  --project "$PROJECT_ID" \
  --display-name "GitHub Cloud Run Deployer" || true
```

如果 service account 已存在，`create` 可能會顯示錯誤；因為命令後面有 `|| true`，可以繼續往下跑。

## 4. 授權 Service Account 部署 Cloud Run

```bash
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member "serviceAccount:${SA_EMAIL}" \
  --role "roles/run.admin"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member "serviceAccount:${SA_EMAIL}" \
  --role "roles/iam.serviceAccountUser"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member "serviceAccount:${SA_EMAIL}" \
  --role "roles/cloudbuild.builds.editor"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member "serviceAccount:${SA_EMAIL}" \
  --role "roles/artifactregistry.admin"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member "serviceAccount:${SA_EMAIL}" \
  --role "roles/storage.admin"
```

## 5. 建立 Workload Identity Federation

這一步讓 GitHub Actions 可以用 OIDC 登入 Google Cloud，不需要建立或上傳 JSON 私鑰。

```bash
gcloud iam workload-identity-pools create "$POOL_ID" \
  --project "$PROJECT_ID" \
  --location "global" \
  --display-name "GitHub Actions" || true

gcloud iam workload-identity-pools providers create-oidc "$PROVIDER_ID" \
  --project "$PROJECT_ID" \
  --location "global" \
  --workload-identity-pool "$POOL_ID" \
  --display-name "GitHub stock-picker" \
  --issuer-uri "https://token.actions.githubusercontent.com" \
  --attribute-mapping "google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.ref=assertion.ref" \
  --attribute-condition "assertion.repository=='tamyu321-source/stock-picker' && assertion.ref=='refs/heads/master'" || true
```

## 6. 允許 GitHub repo 使用這個 Service Account

```bash
WIF_PROVIDER="projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/providers/${PROVIDER_ID}"
WIF_MEMBER="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/attribute.repository/${REPO}"

gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
  --project "$PROJECT_ID" \
  --role "roles/iam.workloadIdentityUser" \
  --member "$WIF_MEMBER"

printf 'GCP_WORKLOAD_IDENTITY_PROVIDER=%s\n' "$WIF_PROVIDER"
printf 'GCP_SERVICE_ACCOUNT=%s\n' "$SA_EMAIL"
```

請保留最後輸出的兩個值，下一步要填到 GitHub Variables。

## 7. 設定 GitHub Repository Variables

到 GitHub repository：

```text
Settings -> Secrets and variables -> Actions -> Variables -> New repository variable
```

新增：

```text
GCP_WORKLOAD_IDENTITY_PROVIDER = projects/.../locations/global/workloadIdentityPools/github-actions/providers/github
GCP_SERVICE_ACCOUNT = github-cloud-run-deployer@stock-picker-prod.iam.gserviceaccount.com
CLOUD_RUN_API_ACCESS_KEYS = 19940710
VITE_API_KEY = 19940710
```

如果你在 Cloud Shell 已安裝並登入 GitHub CLI，也可以用：

```bash
gh variable set GCP_WORKLOAD_IDENTITY_PROVIDER --body "$WIF_PROVIDER"
gh variable set GCP_SERVICE_ACCOUNT --body "$SA_EMAIL"
gh variable set CLOUD_RUN_API_ACCESS_KEYS --body "19940710"
gh variable set VITE_API_KEY --body "19940710"
```

## 8. 第一次部署 Cloud Run

把本 repo 的變更 commit 並 push 到 `master` 後，GitHub Actions 會出現：

```text
Actions -> Deploy Cloud Run API
```

你也可以手動執行：

```text
Deploy Cloud Run API -> Run workflow
```

Cloud Run workflow 會使用：

```text
--allow-unauthenticated
--max-instances=2
ALLOWED_ORIGINS=https://tamyu321-source.github.io
API_ACCESS_KEYS=19940710
```

## 9. 取得 Cloud Run URL

```bash
API_URL="$(gcloud run services describe stock-picker-api \
  --region asia-east1 \
  --format "value(status.url)")"

echo "$API_URL"
```

測試 API：

```bash
curl -H "X-Stock-Picker-Key: 19940710" "$API_URL/api/health"
```

## 10. 讓 GitHub Pages 指向 Cloud Run

把 Cloud Run URL 設成 GitHub Repository Variable：

```bash
gh variable set VITE_API_BASE_URL --body "$API_URL"
```

或到 GitHub UI 新增：

```text
VITE_API_BASE_URL = https://你的-cloud-run-url.a.run.app
```

注意 URL 最後不要加 `/`。

## 11. 部署 GitHub Pages

到 GitHub Actions 手動跑一次：

```text
Deploy GitHub Pages -> Run workflow
```

之後每次 push 到 `master`：

- 前端會由 GitHub Pages workflow 自動更新。
- 後端相關檔案有變更時，Cloud Run workflow 會自動更新 API。

目前 Cloud Run workflow 監聽：

```text
backend/**
requirements.txt
Dockerfile
.gcloudignore
.github/workflows/deploy-cloud-run.yml
```

## 12. 控費建議

目前已設定：

```text
--max-instances=2
```

建議再到 Google Cloud Console 設定 Billing budget alert，例如 50%、90%、100% 通知。

提醒：`19940710` 會被打包進 GitHub Pages 前端，因此它是共享門禁，不是真正私密密鑰。它可以擋掉沒有 header 的隨機請求；若未來要更強保護，可以再升級成登入或後端發 token。
