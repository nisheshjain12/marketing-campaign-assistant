# Google Ads setup guide (real API — optional)

> **Current project:** Google Ads is **mocked**. You do not need this guide to run the app. See [MOCK_MODE.md](./MOCK_MODE.md).

This document is for when you replace the mock with the real API.

This backend can publish **Search campaigns** to a Google Ads **test account** using the official Python library.

## What you need

| Credential | Where it lives | Purpose |
|------------|----------------|---------|
| Developer token | `google-ads.yaml` | API access |
| OAuth client ID & secret | `google-ads.yaml` | Authentication |
| Refresh token | `google-ads.yaml` | Long-lived access |
| Login customer ID | `google-ads.yaml` | Manager (MCC) account |
| Customer account ID | `.env` → `GOOGLE_ADS_CUSTOMER_ID` | Account where campaigns are created |

## Step 1 — Google Ads test account

1. Go to [Google Ads](https://ads.google.com/) and create an account (or use a test account).
2. Note your **customer ID** (10 digits, often shown as `123-456-7890`).
3. For `.env`, use **numbers only**: `1234567890`.

If you use a Manager (MCC) account, put the MCC ID in `login_customer_id` in the yaml file.

## Step 2 — Developer token

1. In Google Ads, open **Tools & settings → Setup → API Center**.
2. Apply for a developer token.
3. For test accounts, a **Test account** token is enough to finish this assignment.

## Step 3 — Google Cloud OAuth credentials

1. Open [Google Cloud Console](https://console.cloud.google.com/).
2. Create/select a project.
3. Enable **Google Ads API**.
4. Go to **APIs & Services → Credentials**.
5. Create **OAuth client ID** (Desktop app or Web application).
6. Save **Client ID** and **Client secret**.

## Step 4 — Refresh token

Google provides a helper script in the official repo:

```powershell
pip install google-ads
```

Follow Google's guide: [OAuth2 desktop flow](https://developers.google.com/google-ads/api/docs/client-libs/python/oauth-web)

You will run a small script once, sign in with the Google account that has access to your Ads account, and copy the **refresh token**.

## Step 5 — Create config files

```powershell
cd backend
copy google-ads.yaml.example google-ads.yaml
copy .env.example .env
```

Edit **`google-ads.yaml`** (never commit this file):

```yaml
developer_token: YOUR_DEV_TOKEN
client_id: YOUR_CLIENT_ID.apps.googleusercontent.com
client_secret: YOUR_CLIENT_SECRET
refresh_token: YOUR_REFRESH_TOKEN
login_customer_id: YOUR_MANAGER_OR_SAME_CUSTOMER_ID
use_proto_plus: true
```

Edit **`.env`**:

```
GOOGLE_ADS_CUSTOMER_ID=1234567890
```

## Step 6 — Install dependency

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Step 7 — Test publish flow

Terminal 1 — start backend:

```powershell
python run.py
```

Terminal 2 — create a draft, then publish:

```powershell
# 1) Create draft locally
$body = @{
  name = "API Search Test"
  objective = "TRAFFIC"
  campaign_type = "SEARCH"
  daily_budget = 10
  start_date = "2026-09-01"
  ad_group_name = "Main"
  ad_headline = "Great deals"
  ad_description = "Shop our sale today"
  asset_url = "https://www.example.com"
} | ConvertTo-Json

$created = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:5000/api/campaigns -Body $body -ContentType "application/json"
$id = $created.data.id

# 2) Publish to Google Ads
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:5000/api/campaigns/$id/publish"

# 3) Pause (optional safety step)
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:5000/api/campaigns/$id/pause"
```

## Safety built into our code

- Google campaign is created with status **PAUSED**
- Ad is created **PAUSED**
- If `start_date` is in the past, we push it to **tomorrow**

This matches the assignment: *"Inactive campaigns (or control by start date)"*.

## Verify in Google Ads UI

1. Sign in to Google Ads.
2. Go to **Campaigns** — you should see your campaign name.
3. Status should be **Paused**.
4. Your API response includes `google_campaign_id`.

## Common errors

| Error | Likely cause |
|-------|----------------|
| `GOOGLE_ADS_CUSTOMER_ID is not set` | Add to `.env` |
| `File google-ads.yaml was not found` | Copy example file to `backend/google-ads.yaml` |
| `USER_PERMISSION_DENIED` | Wrong customer ID or account not linked to OAuth user |
| `DEVELOPER_TOKEN_NOT_APPROVED` | Use a test account with a test token, or wait for approval |
| `Invalid date` / policy errors | Check headline/description length; use a valid final URL |

## PR suggestion

Split Phase 5 into one PR:

**Branch:** `feat/google-ads-publish-and-pause`

**Files:** `google_ads_service.py`, `campaign_service.py`, `routes/campaigns.py`, `errors.py`, `config.py`, `requirements.txt`, docs, examples.

**Do not commit:** `google-ads.yaml`, `.env`
