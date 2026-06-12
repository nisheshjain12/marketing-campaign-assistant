# Marketing Campaign Assistant

A full-stack web application to create, manage, and publish digital marketing campaigns from a single interface.

---

## 1. What This App Does (For Everyone)

- **What problem it solves**
  - Managing online ads normally means logging into Google Ads, navigating multiple screens, and filling complex forms
  - This app gives you one simple page to create and manage campaigns without needing to touch Google Ads directly

- **Create a campaign**
  - Fill in a short form: campaign name, goal (traffic, leads, or sales), daily budget, start and end dates
  - Write the ad text — a headline and a short description that people will see in your ad
  - Click **Save Locally** — the campaign is saved to the database with a grey **DRAFT** badge

- **See all your campaigns**
  - Every saved campaign appears in a table below the form
  - The table shows: name, goal, daily budget, start date, status, and Google Campaign ID

- **Publish to Google Ads**
  - Click the green **Publish** button next to any draft campaign
  - The app sends the campaign to Google Ads and the status badge turns green: **PUBLISHED**
  - A Google Campaign ID appears in the table confirming it's live

- **Pause a campaign**
  - Click the amber **Pause** button next to any published campaign to stop it temporarily
  - Status changes to **PAUSED** — no more spend until you decide to re-publish

- **Safe to publish**
  - The app publishes to a **real Google Ads test account** — campaigns are always created **PAUSED**, so a test account is never charged
  - Prefer to explore without credentials? Flip on an **offline mock** (`GOOGLE_ADS_USE_MOCK=true`) that simulates publishing with no API calls — no Google account needed

---

## 2. Technical Overview

### Stack

- **Frontend** — React 18, Vite 4, Axios
- **Backend** — Python 3, Flask 3, Flask-CORS
- **Database** — PostgreSQL, SQLAlchemy ORM, Flask-Migrate (Alembic)
- **Google Ads** — Real Google Ads **REST API** via `requests` (HTTPS, no gRPC; API `v22`); optional offline mock

### Architecture

```
Browser (React — port 5173)
    │  HTTP/JSON via Axios
    ▼
Flask REST API (port 5000)
    │  SQLAlchemy ORM
    ▼
PostgreSQL (campaigns table)
    │  google_ads_service.py — HTTPS/REST via requests
    ▼
Google Ads REST API (v22) — creates a real PAUSED Search campaign
   (or an offline mock when GOOGLE_ADS_USE_MOCK=true)
```

### Backend

- **App factory** — `backend/app/__init__.py` creates the Flask app, registers CORS, blueprints, and error handlers
- **Routes** — `backend/app/routes/campaigns.py` — thin HTTP layer, delegates to service

  | Method | Endpoint | Description |
  |--------|----------|-------------|
  | `GET` | `/api/health` | Health check |
  | `GET` | `/api/campaigns` | List all campaigns (newest first) |
  | `POST` | `/api/campaigns` | Create campaign (status: `DRAFT`) |
  | `POST` | `/api/campaigns/<id>/publish` | Publish to Google Ads (status: `PUBLISHED`) |
  | `POST` | `/api/campaigns/<id>/pause` | Pause campaign (status: `PAUSED`) |

- **Service layer** — `backend/app/services/campaign_service.py` — all business logic and validation
  - Required fields: `name`, `objective`, `daily_budget`, `start_date`, `ad_group_name`, `ad_headline`, `ad_description`
  - `daily_budget` must be a positive integer
  - `end_date` must be on or after `start_date` if provided
  - Status transitions enforced: cannot publish twice, cannot pause a draft

- **Google Ads integration** — `backend/app/services/google_ads_service.py`
  - `publish_search_campaign()` creates Budget → Search Campaign (**PAUSED**) → Ad Group → Responsive Search Ad in a real Google Ads test account, and returns the real campaign ID
  - `pause_campaign()` sets the Google Ads campaign status to PAUSED
  - Calls the Google Ads **REST** `…:mutate` endpoints directly with `requests` (no gRPC / `google-ads` library); fetches an OAuth access token from the refresh token per request
  - API pinned to `v22` (newest with the simple `start_date`/`end_date` fields); sets `contains_eu_political_advertising` (required v22+); auto-pads to the 3-headline / 2-description RSA minimum
  - Set `GOOGLE_ADS_USE_MOCK=true` for an offline mock that returns a fake ID with no API calls — see [docs/MOCK_MODE.md](backend/docs/MOCK_MODE.md)
  - Full credential setup: [docs/GOOGLE_ADS_SETUP.md](backend/docs/GOOGLE_ADS_SETUP.md)

- **Database schema** — single `campaigns` table

  | Column | Type | Notes |
  |--------|------|-------|
  | `id` | UUID | Auto-generated primary key |
  | `name` | String | Campaign name |
  | `objective` | String | `TRAFFIC`, `LEADS`, `SALES`, `AWARENESS` |
  | `campaign_type` | String | `SEARCH` (default) |
  | `daily_budget` | Integer | USD per day |
  | `start_date` | Date | Required |
  | `end_date` | Date | Optional |
  | `status` | String | `DRAFT` → `PUBLISHED` → `PAUSED` |
  | `google_campaign_id` | String | Null until published |
  | `ad_group_name` | String | Ad group name |
  | `ad_headline` | String | Ad title text |
  | `ad_description` | Text | Ad body text |
  | `asset_url` | Text | Optional landing page URL |
  | `created_at` | Timestamp | UTC, auto-set on create |

- **Error responses** — consistent JSON shape across all endpoints
  ```json
  { "error": { "message": "...", "details": ["field is required", "..."] } }
  ```

### Frontend

- **`src/App.jsx`** — top-level component; fetches campaign list on load and after every action
- **`src/components/CampaignForm.jsx`** — controlled form; posts to `POST /api/campaigns`; clears on success
- **`src/components/CampaignList.jsx`** — renders campaigns as a table with coloured status badges and action buttons
- **`src/api/campaigns.js`** — Axios instance; base URL reads from `VITE_API_URL` env var (defaults to `http://127.0.0.1:5000`)

---

## 3. How to Run and Test Locally

### Prerequisites

- [Python 3.10+](https://www.python.org/downloads/)
- [Node.js 18+](https://nodejs.org/) (includes npm)
- [PostgreSQL 14+](https://www.postgresql.org/download/) installed and running

---

### Step 1 — Clone the repository

```bash
git clone https://github.com/nisheshjain12/marketing-campaign-assistant.git
cd marketing-campaign-assistant
```

---

### Step 2 — Create the database

```bash
psql -U postgres
```
```sql
CREATE DATABASE campaign_assistant;
\q
```

---

### Step 3 — Configure the backend

```bash
cd backend
cp .env.example .env    # Mac/Linux
# OR on Windows PowerShell:
copy .env.example .env
```

- Open `.env` and set your PostgreSQL password (and the Google Ads target account):
  ```
  DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/campaign_assistant
  CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
  GOOGLE_ADS_CUSTOMER_ID=1234567890   # your test client account (digits only)
  GOOGLE_ADS_USE_MOCK=false           # set true to skip Google and use the offline mock
  ```

- **Google Ads credentials** — to publish for real, create `backend/google-ads.yaml`
  with your developer token, OAuth client, refresh token, and `login_customer_id`,
  following [docs/GOOGLE_ADS_SETUP.md](backend/docs/GOOGLE_ADS_SETUP.md). To skip this
  entirely, set `GOOGLE_ADS_USE_MOCK=true` and no credentials are needed.

---

### Step 4 — Install backend dependencies and apply migrations

```bash
# Create and activate virtual environment
python -m venv venv

# Mac/Linux:
source venv/bin/activate
# Windows PowerShell:
.\venv\Scripts\Activate.ps1

pip install -r requirements.txt

# Apply database migrations (creates the campaigns table)
flask db upgrade
```

---

### Step 5 — Start the backend server

```bash
python run.py
```

- Expected output: `* Running on http://127.0.0.1:5000`
- Leave this terminal open

---

### Step 6 — Install and start the frontend

Open a **second terminal**:

```bash
cd frontend
npm install
npm run dev
```

- Expected output: `➜  Local:   http://localhost:5173/`
- Open [http://localhost:5173](http://localhost:5173) in your browser

---

### Step 7 — Test the full workflow in the browser

- **Health check** — visit `http://127.0.0.1:5000/api/health` → should return `{"data":{"status":"ok"}}`
- **Create a campaign** — fill the form and click **Save Locally**
  - Campaign appears in the list with a grey **DRAFT** badge
  - `Google ID` column shows `—`
- **Test validation** — submit the form with an empty name or budget of `0`
  - A red error message should appear; no campaign should be added to the list
- **Publish** — click the green **Publish** button on a DRAFT row
  - Status changes to **PUBLISHED** (green badge)
  - A real Google Campaign ID appears in the table; the campaign is created **PAUSED** in your Google Ads test account (verify it in the Google Ads UI)
  - *(With `GOOGLE_ADS_USE_MOCK=true`, a fake 10-digit ID appears instead and nothing is sent to Google)*
- **Pause** — click the amber **Pause** button on a PUBLISHED row
  - Status changes to **PAUSED** (amber badge)
- **Persistence check** — stop the backend (Ctrl+C), restart it (`python run.py`), reload the browser
  - All campaigns should still be there (data lives in PostgreSQL)

---

### Step 8 — Run the automated backend tests

```bash
# Inside backend/ with venv active
python test_backend.py
```

- Expected result: `=== Results: 33 passed, 0 failed ===`
- Covers: health check, create, validation errors, list ordering, publish, pause, not-found, business rules, and database persistence

---

### Troubleshooting

| Problem | Fix |
|---------|-----|
| `flask db upgrade` fails | Check `DATABASE_URL` in `.env` is correct and PostgreSQL is running |
| Browser shows "Could not load campaigns" | Confirm Flask is running on port 5000; frontend calls `http://127.0.0.1:5000` not `localhost` |
| CORS error in browser console | Add `CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173` to `backend/.env` and restart Flask |
| `psycopg2` install error on Linux | Run `sudo apt install libpq-dev` first |
| Port 5173 already in use | Stop other Vite processes or change port in `frontend/vite.config.js` |
