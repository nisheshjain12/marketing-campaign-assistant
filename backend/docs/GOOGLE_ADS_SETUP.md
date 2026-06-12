# Google Ads setup guide (real API)

This backend publishes real **Search** campaigns to a Google Ads **test account**
over the Google Ads **REST API** (plain HTTPS via `requests` — no gRPC or
`google-ads` client library). Campaigns are created **PAUSED**, so a test account
is never charged.

> Want to run the app without Google credentials (e.g. frontend work)? Set
> `GOOGLE_ADS_USE_MOCK=true` in `.env` — see [MOCK_MODE.md](./MOCK_MODE.md).

---

## The one thing that trips everyone up

A **test account** is only a test account if it lives under a **test manager
account**. And a *test* manager can **only be created from a Google account that
is NOT already linked to a production Google Ads manager account**, using a
dedicated button. Creating a manager the normal way produces a *production*
manager, and a Test-level developer token cannot touch production accounts
(you'll get `CUSTOMER_NOT_ENABLED`).

So this setup uses **two Google accounts**:

| Google account | Owns | Used for |
|----------------|------|----------|
| **Account A** (your main) | A manager account + the Cloud project | Getting the **developer token**; hosting the OAuth client |
| **Account B** (separate, never used for Ads) | The **test manager** + **test client** | Creating test accounts; generating the **refresh token** |

The developer token from Account A works against test accounts owned by
Account B — Google explicitly allows this for Test-level tokens.

---

## Credentials you end up with

| Credential | Lives in | From |
|------------|----------|------|
| Developer token | `google-ads.yaml` | Account A manager → API Center |
| OAuth client ID & secret | `google-ads.yaml` | Cloud Console (Account A) |
| Refresh token | `google-ads.yaml` | OAuth flow signed in as **Account B** |
| `login_customer_id` | `google-ads.yaml` | **Test manager** ID (Account B) |
| `GOOGLE_ADS_CUSTOMER_ID` | `.env` | **Test client** ID (Account B) |

---

## Step 1 — Manager account for the developer token (Account A)

1. Sign in as **Account A** and create a manager account at
   <https://ads.google.com/home/tools/manager-accounts/> → **Manage my accounts**.
   (The developer token lives in a manager account's API Center; a regular ad
   account doesn't have one.)

## Step 2 — Developer token (Account A)

1. In that manager account, open <https://ads.google.com/aw/apicenter>.
2. Complete the API access form and accept the terms.
3. A developer token is issued at **Test Account Access** level — that's all you
   need; it works on test accounts immediately, no approval wait.

## Step 3 — TEST manager account (Account B) ⚠️ the critical step

1. Sign in as **Account B** only (use an Incognito window to avoid mixing
   sessions). Account B must have **no** existing Google Ads accounts.
2. Go to the [Test accounts doc page](https://developers.google.com/google-ads/api/docs/best-practices/test-accounts)
   and click the blue **"Create a test manager account"** button there.
3. Finish setup (name, country, currency, timezone — no billing).
4. ✅ **Verify:** the account shows a red **"Test account"** label. If it
   doesn't, it was created as production — start over with a fresh account.
5. Note the manager ID → this is **`login_customer_id`**.

## Step 4 — Test client account (Account B)

1. Inside the test manager: **Accounts → Sub-account settings → +  Create new account**.
2. It's automatically a **test account** (red "Test account" label; shows as
   "Cancelled" in the UI — that's normal for test accounts).
3. Note its ID → this is **`GOOGLE_ADS_CUSTOMER_ID`**.

## Step 5 — Google Cloud project + OAuth client (Account A)

1. <https://console.cloud.google.com/> → create a project.
2. **APIs & Services → Library** → enable **Google Ads API**.
3. **Google Auth Platform** (formerly OAuth consent screen) → configure: User
   type **External**, app name, support/contact email.
4. **Clients → Create client → Desktop app** → **Download JSON** and save it in
   `backend/` (e.g. `client_secret_XXX.json`). It holds the **client ID & secret**.

## Step 6 — Allow Account B to authorize (Account A)

Because the OAuth app is in "Testing" mode, only listed users may sign in:

1. **Google Auth Platform → Audience → Test users → Add users**.
2. Add **Account B's email** and save.

## Step 7 — Refresh token (signed in as Account B)

A small helper (`get_refresh_token.py`) is git-ignored and not committed; create
it with this content if it's missing:

```python
import argparse
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/adwords"]

def main(path):
    flow = InstalledAppFlow.from_client_secrets_file(path, scopes=SCOPES)
    creds = flow.run_local_server(
        host="127.0.0.1", port=8080, open_browser=False,
        access_type="offline", prompt="consent",
        authorization_prompt_message="Open this URL as Account B:\n\n{url}\n",
    )
    print("\nRefresh token:\n", creds.refresh_token)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("-c", "--client_secrets_path", required=True)
    main(p.parse_args().client_secrets_path)
```

Run it (from `backend/`, with the venv active). The helper needs the one-time dev
dependency `google-auth-oauthlib` (only for generating the token — the running
app does not use it):

```powershell
.\venv\Scripts\python.exe -m pip install google-auth-oauthlib
.\venv\Scripts\python.exe get_refresh_token.py -c "client_secret_XXX.json"
```

It prints a URL — open it in the browser/profile signed in as **Account B**,
approve (click **Advanced → Go to … (unsafe)** past the "unverified app"
screen), and copy the printed refresh token.

> We use `run_local_server` instead of Google's `generate_user_credentials.py`
> sample because the sample's hand-rolled socket parser crashes
> (`'NoneType' object has no attribute 'group'`) when the browser sends a stray
> request like `/favicon.ico` to the callback port.

## Step 8 — Config files

`backend/google-ads.yaml` (git-ignored — never commit):

```yaml
developer_token: "YOUR_DEV_TOKEN"            # Account A
client_id: "YOUR_CLIENT_ID.apps.googleusercontent.com"
client_secret: "YOUR_CLIENT_SECRET"
refresh_token: "YOUR_REFRESH_TOKEN"          # Account B
login_customer_id: "YOUR_TEST_MANAGER_ID"    # digits only, no dashes
```

`backend/.env`:

```
GOOGLE_ADS_CUSTOMER_ID=YOUR_TEST_CLIENT_ID   # digits only, no dashes
GOOGLE_ADS_USE_MOCK=false
```

## Step 9 — Install and test

```powershell
cd backend
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

In another terminal:

```powershell
$body = @{
  name = "API Search Test"; objective = "TRAFFIC"; campaign_type = "SEARCH"
  daily_budget = 10; start_date = "2026-09-01"
  ad_group_name = "Main"; ad_headline = "Great deals"
  ad_description = "Shop our sale today"; asset_url = "https://www.example.com"
} | ConvertTo-Json

$c = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:5000/api/campaigns -Body $body -ContentType "application/json"
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:5000/api/campaigns/$($c.data.id)/publish"
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:5000/api/campaigns/$($c.data.id)/pause"
```

A successful publish returns `status: PUBLISHED` and a real numeric
`google_campaign_id`. Verify in the Google Ads UI (signed in as Account B):
the campaign appears under the test client account with status **Paused**.

---

## How the integration works

See [`app/services/google_ads_service.py`](../app/services/google_ads_service.py).
It talks to Google over plain **HTTPS/REST** with `requests` — no gRPC.

- **OAuth:** the refresh token (+ client id/secret) is exchanged at
  `https://oauth2.googleapis.com/token` for a short-lived access token, sent as
  `Authorization: Bearer …`. Every call also sends `developer-token` and
  `login-customer-id` headers.
- **Endpoints:** `POST …:mutate` under
  `https://googleads.googleapis.com/v22/customers/<customer_id>/` —
  `campaignBudgets`, `campaigns`, `adGroups`, `adGroupAds`. Pause and resume
  re-use `campaigns:mutate` with an `update` (`status=PAUSED` / `ENABLED`) and
  `updateMask=status`.
- **API version is pinned to `v22`.** v23+ renamed `startDate` / `endDate` to
  `startDateTime` / `endDateTime`; v22 is the newest version with the simple
  date fields.
- **Publish** creates: Campaign Budget → Search Campaign (**PAUSED**) → Ad Group
  → Responsive Search Ad (**PAUSED**), and returns the campaign ID.
- **Safety:** campaign and ad are PAUSED; a past start date is pushed to tomorrow.
  A test account can't be charged regardless.
- **Required field (v22+):** `containsEuPoliticalAdvertising` is set to
  `DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING`.
- **Responsive Search Ads** require ≥3 headlines and ≥2 descriptions; the service
  auto-pads from the single headline / description (truncated to 30 / 90 chars).
- **Unique names:** a short suffix is appended to budget/campaign names so
  re-runs never collide.

---

## Troubleshooting

| Error | Cause / fix |
|-------|-------------|
| `CUSTOMER_NOT_ENABLED` | The target account isn't a real test account (its manager is production). Recreate the test manager per **Step 3** with a fresh Google account. |
| `The developer token is only approved for use with test accounts…` | You're hitting a **production** account with a Test-level token. Use a test account, or apply for Basic access. |
| `Unknown field for Campaign: start_date` | API version is v23+. Pin to `v22` (already done via `_API_VERSION`). |
| `The required field was not present` → `contains_eu_political_advertising` | v22+ requires this field (already set in the code). |
| `'NoneType' object has no attribute 'group'` during token generation | Google's sample script choking on a stray callback request. Use the `run_local_server`-based `get_refresh_token.py` above. |
| `Access blocked / app not verified` (no Advanced link) | The signing-in account isn't a **Test user** on the OAuth app — add it (**Step 6**). |
| `File google-ads.yaml was not found` | Create `backend/google-ads.yaml` (**Step 8**). |
| `GOOGLE_ADS_CUSTOMER_ID is not set` | Add it to `backend/.env`. |

## Never commit

`google-ads.yaml`, `.env`, `client_secret*.json`, `get_refresh_token.py` — all
git-ignored.
