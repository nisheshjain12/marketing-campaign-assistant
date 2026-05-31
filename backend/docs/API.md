# API documentation

Base URL: `http://localhost:5000`

All responses use JSON. Success payloads are wrapped in `{ "data": ... }`.

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
