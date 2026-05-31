# Database setup (Phase 2)

## 1. Install PostgreSQL

Create a database named `campaign_assistant` (any name is fine if you update `.env`).

Example (psql):

```sql
CREATE DATABASE campaign_assistant;
```

## 2. Python environment

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 3. Environment file

```powershell
copy .env.example .env
```

Edit `.env` and set `DATABASE_URL` to match your Postgres user, password, host, and database name.

## 4. Run migrations

```powershell
$env:FLASK_APP = "run.py"
flask db init
flask db migrate -m "create campaigns table"
flask db upgrade
```

`flask db init` is only needed once. After that, use `migrate` + `upgrade` when the model changes.

## 5. Verify

```powershell
flask shell
```

```python
from app.models import Campaign
from app.extensions import db
c = Campaign(
    name="Test",
    objective="TRAFFIC",
    campaign_type="SEARCH",
    daily_budget=10,
    start_date=__import__("datetime").date(2026, 6, 1),
    ad_group_name="Test Group",
    ad_headline="Buy now",
    ad_description="Great product",
)
db.session.add(c)
db.session.commit()
Campaign.query.all()
```

You should see one row with `status` = `DRAFT`.
