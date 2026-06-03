# Google Ads mock mode

The backend uses a **mock** Google Ads service (`app/services/google_ads_service.py`).
No `google-ads.yaml`, developer token, or OAuth setup is required.

## What still works

| Endpoint | Behavior |
|----------|----------|
| `POST /api/campaigns` | Saves campaign as `DRAFT` in PostgreSQL |
| `GET /api/campaigns` | Lists all campaigns |
| `POST /api/campaigns/<id>/publish` | Sets `status=PUBLISHED` and a fake `google_campaign_id` |
| `POST /api/campaigns/<id>/pause` | Sets `status=PAUSED` |

Publish/pause do **not** call Google. IDs look like real numeric campaign IDs for the UI.

## Run backend

```powershell
cd backend
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

## Switch to real Google Ads later

1. Add `google-ads>=24.0.0` to `requirements.txt`
2. Replace `google_ads_service.py` with the real implementation
3. Add `GOOGLE_ADS_CUSTOMER_ID` to `.env` and `google-ads.yaml`
4. See `GOOGLE_ADS_SETUP.md`
