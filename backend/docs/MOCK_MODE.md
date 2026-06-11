# Google Ads mock mode (offline fallback)

The backend talks to the **real** Google Ads API by default (see
[GOOGLE_ADS_SETUP.md](./GOOGLE_ADS_SETUP.md)). For frontend work or demos without
credentials, you can switch [`app/services/google_ads_service.py`](../app/services/google_ads_service.py)
into an **offline mock** that makes no API calls.

## Enable mock mode

In `backend/.env`:

```
GOOGLE_ADS_USE_MOCK=true
```

No `google-ads.yaml`, developer token, or OAuth setup is required while this is on.

## What each mode does

| Endpoint | Real mode (`false`, default) | Mock mode (`true`) |
|----------|------------------------------|--------------------|
| `POST /api/campaigns` | Saves campaign as `DRAFT` in PostgreSQL | same |
| `GET /api/campaigns` | Lists all campaigns | same |
| `POST /api/campaigns/<id>/publish` | Creates a real **PAUSED** Search campaign in Google Ads, stores the real `google_campaign_id`, sets `status=PUBLISHED` | Sets `status=PUBLISHED` with a fake numeric `google_campaign_id` (no API call) |
| `POST /api/campaigns/<id>/pause` | Sets the Google Ads campaign to PAUSED | Sets `status=PAUSED` (no API call) |

The mock returns realistic-looking numeric IDs so the UI behaves identically.

## Run backend

```powershell
cd backend
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

## Switch back to the real API

Set `GOOGLE_ADS_USE_MOCK=false` (or remove it) and make sure `google-ads.yaml`
and `GOOGLE_ADS_CUSTOMER_ID` are configured per
[GOOGLE_ADS_SETUP.md](./GOOGLE_ADS_SETUP.md).
