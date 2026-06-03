# API documentation

Base URL: `http://localhost:5000`

All responses use JSON. Success payloads are wrapped in `{ "data": ... }`.

> **Google Ads:** Publish and pause use a **mock** service (no real API). See [MOCK_MODE.md](./MOCK_MODE.md).

## Create campaign (local DB only)

**POST** `/api/campaigns`

Saves a campaign to PostgreSQL with `status = "DRAFT"`. Does not call Google Ads.

Request body (`application/json`):

```json
{
  "name": "Summer Sale",
  "objective": "TRAFFIC",
  "campaign_type": "SEARCH",
  "daily_budget": 20,
  "start_date": "2026-06-01",
  "end_date": null,
  "ad_group_name": "Main Group",
  "ad_headline": "Shop now",
  "ad_description": "Limited time offer",
  "asset_url": "https://example.com"
}
```

| Field | Required | Notes |
|-------|----------|-------|
| `name` | yes | |
| `objective` | yes | e.g. `TRAFFIC`, `LEADS`, `SALES` |
| `daily_budget` | yes | Positive integer (dollars) |
| `start_date` | yes | `YYYY-MM-DD` |
| `ad_group_name` | yes | |
| `ad_headline` | yes | |
| `ad_description` | yes | |
| `campaign_type` | no | Defaults to `SEARCH` |
| `end_date` | no | Must be on or after `start_date` |
| `asset_url` | no | |

Response `201`:

```json
{
  "data": {
    "id": "uuid-here",
    "status": "DRAFT",
    "google_campaign_id": null,
    ...
  }
}
```

Response `400` (validation):

```json
{
  "error": {
    "message": "Missing required fields",
    "details": ["name is required"]
  }
}
```

Example:

```powershell
$body = @{
  name = "Winter Promo"
  objective = "LEADS"
  daily_budget = 15
  start_date = "2026-07-01"
  ad_group_name = "Core"
  ad_headline = "Sign up today"
  ad_description = "Free trial"
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri http://127.0.0.1:5000/api/campaigns -Body $body -ContentType "application/json"
```

## List campaigns

**GET** `/api/campaigns`

Returns every campaign stored in PostgreSQL, **newest first**. No request body.

Response `200`:

```json
{
  "data": [
    {
      "id": "uuid-here",
      "name": "Winter Promo",
      "status": "DRAFT",
      "google_campaign_id": null,
      ...
    }
  ]
}
```

If there are no campaigns yet, `data` is an empty array `[]`.

Example:

```powershell
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:5000/api/campaigns
```

To see full JSON in PowerShell:

```powershell
$r = Invoke-RestMethod -Method Get -Uri http://127.0.0.1:5000/api/campaigns
$r.data | ConvertTo-Json -Depth 5
```

## Publish campaign to Google Ads

**POST** `/api/campaigns/<id>/publish`

Reads the campaign from PostgreSQL, assigns a mock `google_campaign_id`, sets `status = "PUBLISHED"`. No external API call.

No request body.

Response `200`:

```json
{
  "data": {
    "id": "uuid-here",
    "status": "PUBLISHED",
    "google_campaign_id": "12345678901",
    ...
  }
}
```

Response `400` — already published or unsupported campaign type.

Response `404` — unknown campaign id.

Example:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:5000/api/campaigns/YOUR-UUID-HERE/publish"
```

## Pause campaign

**POST** `/api/campaigns/<id>/pause`

Mocks pausing in Google Ads and sets local `status = "PAUSED"`.

No request body.

Response `200` — updated campaign with `status: "PAUSED"`.

Example:

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:5000/api/campaigns/YOUR-UUID-HERE/pause"
```

## Health check

**GET** `/api/health`

Verify the backend is running.

Response `200`:

```json
{
  "data": {
    "status": "ok"
  }
}
```

## Run the server

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python run.py
```

Then open `http://localhost:5000/api/health` in a browser or use curl:

```powershell
curl http://localhost:5000/api/health
```
