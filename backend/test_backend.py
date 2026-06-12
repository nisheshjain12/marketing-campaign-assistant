"""
Backend API smoke test — run: python test_backend.py
"""

import json
import os
import sys
import uuid

# Force the offline mock so the suite never calls Google Ads or needs credentials.
os.environ["GOOGLE_ADS_USE_MOCK"] = "true"

from app import create_app

app = create_app()
client = app.test_client()

passed = 0
failed = 0


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name} — {detail}")


def main():
    print("\n=== Backend API test suite ===\n")

    # 1. Health
    print("1. Health")
    r = client.get("/api/health")
    check("GET /api/health returns 200", r.status_code == 200)
    check("Health has data.status ok", r.get_json().get("data", {}).get("status") == "ok")

    # 2. Create campaign — success
    print("\n2. Create campaign (POST /api/campaigns)")
    valid_body = {
        "name": "API Test Campaign",
        "objective": "TRAFFIC",
        "campaign_type": "SEARCH",
        "daily_budget": 25,
        "start_date": "2026-09-01",
        "end_date": "2026-12-01",
        "ad_group_name": "Main Group",
        "ad_headline": "Shop now",
        "ad_description": "Limited offer today",
        "asset_url": "https://www.example.com",
    }
    r = client.post("/api/campaigns", json=valid_body)
    check("Valid create returns 201", r.status_code == 201)
    data = r.get_json().get("data", {})
    campaign_id = data.get("id")
    check("Response has UUID id", campaign_id and len(campaign_id) == 36)
    check("Status is DRAFT", data.get("status") == "DRAFT")
    check("google_campaign_id is null", data.get("google_campaign_id") is None)
    check("campaign_type is SEARCH", data.get("campaign_type") == "SEARCH")

    # 3. Create — validation errors
    print("\n3. Create validation")
    r = client.post("/api/campaigns", data="not json", content_type="text/plain")
    check("Non-JSON body returns 400", r.status_code == 400)

    r = client.post("/api/campaigns", json={"name": "Only name"})
    check("Missing fields returns 400", r.status_code == 400)
    check("Error has details", bool(r.get_json().get("error", {}).get("details")))

    r = client.post(
        "/api/campaigns",
        json={**valid_body, "name": "Bad budget", "daily_budget": 0},
    )
    check("Zero budget returns 400", r.status_code == 400)

    r = client.post(
        "/api/campaigns",
        json={
            **valid_body,
            "name": "Bad dates",
            "start_date": "2026-12-01",
            "end_date": "2026-06-01",
        },
    )
    check("end_date before start_date returns 400", r.status_code == 400)

    # 4. List campaigns
    print("\n4. List campaigns (GET /api/campaigns)")
    r = client.get("/api/campaigns")
    check("List returns 200", r.status_code == 200)
    items = r.get_json().get("data", [])
    check("List is array", isinstance(items, list))
    check("List contains new campaign", any(c.get("id") == campaign_id for c in items))
    if items:
        check("Newest first (our campaign near top)", items[0].get("id") == campaign_id)

    # 5. Publish
    print("\n5. Publish (POST /api/campaigns/<id>/publish)")
    r = client.post(f"/api/campaigns/{campaign_id}/publish")
    check("Publish returns 200", r.status_code == 200)
    pub = r.get_json().get("data", {})
    google_id = pub.get("google_campaign_id")
    check("Status is PUBLISHED", pub.get("status") == "PUBLISHED")
    check("google_campaign_id is set", google_id and google_id.isdigit())

    r = client.post(f"/api/campaigns/{campaign_id}/publish")
    check("Double publish returns 400", r.status_code == 400)

    # 6. Pause
    print("\n6. Pause (POST /api/campaigns/<id>/pause)")
    r = client.post(f"/api/campaigns/{campaign_id}/pause")
    check("Pause returns 200", r.status_code == 200)
    check("Status is PAUSED", r.get_json().get("data", {}).get("status") == "PAUSED")

    r = client.post(f"/api/campaigns/{campaign_id}/pause")
    check("Double pause returns 400", r.status_code == 400)

    # 6b. Resume
    print("\n6b. Resume (POST /api/campaigns/<id>/resume)")
    r = client.post(f"/api/campaigns/{campaign_id}/resume")
    check("Resume returns 200", r.status_code == 200)
    resumed = r.get_json().get("data", {})
    check("Resume sets status back to PUBLISHED", resumed.get("status") == "PUBLISHED")
    check("Resume keeps same google_campaign_id", resumed.get("google_campaign_id") == google_id)

    r = client.post(f"/api/campaigns/{campaign_id}/resume")
    check("Resume of non-paused returns 400", r.status_code == 400)

    # restore PAUSED so the persistence checks below still hold
    client.post(f"/api/campaigns/{campaign_id}/pause")

    # 7. Not found
    print("\n7. Not found")
    fake_id = str(uuid.uuid4())
    r = client.post(f"/api/campaigns/{fake_id}/publish")
    check("Publish unknown id returns 404", r.status_code == 404)

    # 8. Unsupported campaign type
    print("\n8. Publish non-SEARCH")
    r = client.post(
        "/api/campaigns",
        json={**valid_body, "name": "Demand Gen Test", "campaign_type": "DEMAND_GEN"},
    )
    dg_id = r.get_json()["data"]["id"]
    r = client.post(f"/api/campaigns/{dg_id}/publish")
    check("DEMAND_GEN publish returns 400", r.status_code == 400)

    # 9. Pause without publish
    print("\n9. Pause draft")
    r = client.post(
        "/api/campaigns",
        json={**valid_body, "name": "Draft only pause test"},
    )
    draft_id = r.get_json()["data"]["id"]
    r = client.post(f"/api/campaigns/{draft_id}/pause")
    check("Pause draft returns 400", r.status_code == 400)

    r = client.post(f"/api/campaigns/{draft_id}/resume")
    check("Resume draft returns 400", r.status_code == 400)

    # 10. DB connectivity
    print("\n10. Database")
    with app.app_context():
        from app.models import Campaign

        count = Campaign.query.count()
        check("DB query works", count >= 1)
        row = Campaign.query.filter_by(id=campaign_id).first()
        check("Published row persisted", row and row.status == "PAUSED")
        check("google_campaign_id persisted", row and row.google_campaign_id == google_id)

    # 11. Routes registered
    print("\n11. Routes")
    rules = {str(rule.rule): rule.methods for rule in app.url_map.iter_rules()}
    check("/api/health exists", "/api/health" in rules)
    check("/api/campaigns GET+POST", "/api/campaigns" in rules)
    check("/api/campaigns/<id>/publish", "/api/campaigns/<campaign_id>/publish" in rules)
    check("/api/campaigns/<id>/pause", "/api/campaigns/<campaign_id>/pause" in rules)
    check("/api/campaigns/<id>/resume", "/api/campaigns/<campaign_id>/resume" in rules)

    print(f"\n=== Results: {passed} passed, {failed} failed ===\n")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
