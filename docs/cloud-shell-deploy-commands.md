# Cloud Shell Deploy Commands

Use these commands in Google Cloud Shell. Cloud Shell uses bash, so line continuation is `\`, not the PowerShell backtick.

## Enable APIs

```bash
gcloud config set project stock-picker-prod

gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  iamcredentials.googleapis.com
```

## Create GitHub Actions Google Cloud access

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

## Create Workload Identity Federation

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

WIF_PROVIDER="projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/providers/${PROVIDER_ID}"
WIF_MEMBER="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/${POOL_ID}/attribute.repository/${REPO}"

gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
  --project "$PROJECT_ID" \
  --role "roles/iam.workloadIdentityUser" \
  --member "$WIF_MEMBER"

printf 'GCP_WORKLOAD_IDENTITY_PROVIDER=%s\n' "$WIF_PROVIDER"
printf 'GCP_SERVICE_ACCOUNT=%s\n' "$SA_EMAIL"
```

## First manual Cloud Run deploy

Run this after the repo changes are pushed or after the source is available in Cloud Shell.

```bash
gcloud run deploy stock-picker-api \
  --source . \
  --region asia-east1 \
  --allow-unauthenticated \
  --max-instances 2 \
  --set-env-vars ALLOWED_ORIGINS=https://tamyu321-source.github.io,API_ACCESS_KEYS=19940710
```

## Get and test the API URL

```bash
API_URL="$(gcloud run services describe stock-picker-api \
  --region asia-east1 \
  --format "value(status.url)")"

echo "$API_URL"

curl -H "X-Stock-Picker-Key: 19940710" "$API_URL/api/health"
```
