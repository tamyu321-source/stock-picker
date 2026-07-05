# 登入、使用者 key 與管理員設定

這版不再把 `VITE_API_KEY` 打包進 GitHub Pages。前端只顯示登入頁；使用者輸入 key 後，由 Cloud Run 後端驗證並簽發 session token。不同 key 會對應不同使用者，設定、持倉、保存掃描會存到各自的 user state。

## 本地執行

產生管理員密碼 hash：

```powershell
python -m backend.auth_store hash-password "你的管理員密碼"
```

啟動後端：

```powershell
$env:API_ACCESS_KEYS="19940710"
$env:ADMIN_USERNAME="admin"
$env:ADMIN_PASSWORD_HASH="上一步產生的hash"
$env:AUTH_SESSION_SECRET="請換成一串長隨機字串"
$env:AUTH_STORE_PATH="$PWD\.local-auth-store.json"
python -m backend.app
```

啟動前端：

```powershell
$env:VITE_API_PROXY_TARGET="http://127.0.0.1:8000"
npm run dev
```

打開 Vite 顯示的 `/stock-picker/index.html`，普通登入輸入 `19940710`；管理員登入輸入 `ADMIN_USERNAME` 和原始管理員密碼。

## GitHub Pages 變數

GitHub Pages 只需要知道 API URL：

```powershell
gh variable set VITE_API_BASE_URL --body "https://你的-cloud-run-url.a.run.app"
```

不要再設定 `VITE_API_KEY`。凡是 `VITE_` 開頭的值都會被打包到公開 JS 裡，不適合放密碼或真正的 key。

## Cloud Run 變數與 Secrets

Repository Variables：

```powershell
gh variable set CLOUD_RUN_API_ACCESS_KEYS --body "19940710"
gh variable set STOCK_PICKER_ADMIN_USERNAME --body "admin"
```

Repository Secrets：

```powershell
python -m backend.auth_store hash-password "你的管理員密碼"
gh secret set STOCK_PICKER_ADMIN_PASSWORD_HASH --body "上一步產生的hash"
gh secret set STOCK_PICKER_AUTH_SESSION_SECRET --body "請換成一串長隨機字串"
```

`CLOUD_RUN_API_ACCESS_KEYS` 可以放多個初始 key，用逗號分隔，例如：

```text
19940710,another-user-key,third-user-key
```

這些 key 只會在後端 bootstrap 使用；後端會保存 hash，不保存明文。

## 持久化使用者資料

如果沒有設定資料 bucket，Cloud Run 會使用 `/tmp/stock-picker-auth-store.json`，這只適合測試，容器重啟後可能遺失管理員新增的使用者與 user state。

正式使用時建議建立 Cloud Storage bucket，並設定：

```powershell
gh variable set STOCK_PICKER_DATA_BUCKET --body "你的-bucket-name"
```

workflow 會把 bucket 掛載到 `/data`，並把 `AUTH_STORE_PATH` 設為 `/data/auth-store.json`。Cloud Run 官方文件說明 Cloud Storage volume mount 會把 bucket 內容呈現成容器內的檔案系統，應用可以用一般檔案 API 讀寫；但也要注意 Cloud Storage FUSE 對同一檔案多寫入沒有完整檔案鎖，如果之後要支援更多同時使用者，應改用資料庫。
本 repo 的 Cloud Run workflow 在設定 `STOCK_PICKER_DATA_BUCKET` 時會自動改成 `--max-instances 1`，避免多個 instance 同時寫同一份 user state JSON。

參考：<https://docs.cloud.google.com/run/docs/configuring/services/cloud-storage-volume-mounts>

## 使用方式

1. 使用者打開 GitHub Pages。
2. 輸入自己的 key，例如 `19940710`。
3. 後端驗證 key，回傳 session token。
4. 前端載入該 key 對應的 settings、saved scans、portfolio。
5. 管理員用帳密登入 Admin，新增 key、停用 key、重置某個使用者資料。

如果要換管理員密碼，重新產生 `STOCK_PICKER_ADMIN_PASSWORD_HASH` 並更新 GitHub Secret，再重新部署 Cloud Run。
