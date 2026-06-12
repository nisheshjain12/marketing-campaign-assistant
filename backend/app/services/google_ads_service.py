"""
Google Ads integration (REST).

Publishes a local campaign as a real **Search** campaign (created PAUSED so the
account is never charged) and pauses a campaign by its Google campaign ID.

This talks to the Google Ads API over plain **HTTPS/REST** using `requests` —
no gRPC / `google-ads` client library. Each operation is a POST to a
`...:mutate` endpoint.

Credentials are read from ``backend/google-ads.yaml`` (developer token, OAuth
client id/secret, refresh token, login_customer_id). The target account is read
from the ``GOOGLE_ADS_CUSTOMER_ID`` environment variable.

Set ``GOOGLE_ADS_USE_MOCK=true`` in ``.env`` to fall back to the offline mock
(no API calls) — handy for frontend work without credentials.
"""

import os
import random
import uuid
from datetime import date, timedelta

from app.errors import GoogleAdsError
from app.models import Campaign

# Offline fallback: set GOOGLE_ADS_USE_MOCK=true in .env to skip real API calls.
USE_MOCK = os.getenv("GOOGLE_ADS_USE_MOCK", "false").strip().lower() in ("1", "true", "yes")

# google-ads.yaml lives in the backend/ directory (two levels up from this file).
_YAML_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "google-ads.yaml")
)

# Pin the API version explicitly. v22 is the newest version that still uses the
# simple Campaign.startDate / endDate fields (v23+ renamed them to *DateTime).
_API_VERSION = "v22"
_BASE_URL = f"https://googleads.googleapis.com/{_API_VERSION}"
_TOKEN_URL = "https://oauth2.googleapis.com/token"

# Responsive Search Ad field limits / minimums enforced by the API.
_HEADLINE_MAX = 30
_DESCRIPTION_MAX = 90
_MIN_HEADLINES = 3
_MIN_DESCRIPTIONS = 2


# --------------------------------------------------------------------------- #
# Public API — same contract the rest of the app already calls.
# --------------------------------------------------------------------------- #
def publish_search_campaign(campaign: Campaign) -> str:
    """Create a PAUSED Search campaign in Google Ads; return its numeric ID."""
    if USE_MOCK:
        return _mock_publish(campaign)
    return _real_publish(campaign)


def pause_campaign(google_campaign_id: str) -> None:
    """Set a Google Ads campaign's status to PAUSED."""
    if USE_MOCK:
        return _mock_pause(google_campaign_id)
    return _real_pause(google_campaign_id)


def resume_campaign(google_campaign_id: str) -> None:
    """Set a Google Ads campaign's status to ENABLED (resume a paused campaign)."""
    if USE_MOCK:
        return _mock_resume(google_campaign_id)
    return _real_resume(google_campaign_id)


# --------------------------------------------------------------------------- #
# Offline mock.
# --------------------------------------------------------------------------- #
def _mock_publish(campaign: Campaign) -> str:
    _ = campaign  # same fields would be sent to Google Ads in production
    return str(random.randint(1_000_000_000, 9_999_999_999))


def _mock_pause(google_campaign_id: str) -> None:
    _ = google_campaign_id


def _mock_resume(google_campaign_id: str) -> None:
    _ = google_campaign_id


# --------------------------------------------------------------------------- #
# Real Google Ads implementation (REST).
# --------------------------------------------------------------------------- #
def _real_publish(campaign: Campaign) -> str:
    customer_id, headers = _rest_context()

    # Unique suffix so re-runs never collide on budget/campaign names.
    unique = uuid.uuid4().hex[:8]

    budget_resource = _create_budget(customer_id, headers, campaign, unique)
    campaign_resource = _create_campaign(
        customer_id, headers, campaign, budget_resource, unique
    )
    ad_group_resource = _create_ad_group(customer_id, headers, campaign, campaign_resource)
    _create_responsive_search_ad(customer_id, headers, campaign, ad_group_resource)

    return campaign_resource.split("/")[-1]


def _real_pause(google_campaign_id: str) -> None:
    _set_campaign_status(google_campaign_id, "PAUSED")


def _real_resume(google_campaign_id: str) -> None:
    _set_campaign_status(google_campaign_id, "ENABLED")


def _set_campaign_status(google_campaign_id: str, status: str) -> None:
    """Update only the status of an existing campaign (PAUSED / ENABLED)."""
    customer_id, headers = _rest_context()
    resource_name = f"customers/{customer_id}/campaigns/{google_campaign_id}"
    _mutate(
        "campaigns",
        customer_id,
        headers,
        [{"update": {"resourceName": resource_name, "status": status}, "updateMask": "status"}],
    )


def _create_budget(customer_id, headers, campaign, unique):
    operations = [
        {
            "create": {
                "name": f"{campaign.name} Budget {unique}",
                "amountMicros": str(int(campaign.daily_budget) * 1_000_000),
                "deliveryMethod": "STANDARD",
                "explicitlyShared": False,
            }
        }
    ]
    result = _mutate("campaignBudgets", customer_id, headers, operations)
    return result["results"][0]["resourceName"]


def _create_campaign(customer_id, headers, campaign, budget_resource, unique):
    start, end = _campaign_dates(campaign)
    create = {
        "name": f"{campaign.name} [{unique}]",
        "advertisingChannelType": "SEARCH",
        # PAUSED so the campaign never serves and the account is never charged.
        "status": "PAUSED",
        # Required since v22: declare the campaign carries no EU political ads.
        "containsEuPoliticalAdvertising": "DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING",
        "manualCpc": {"enhancedCpcEnabled": False},
        "campaignBudget": budget_resource,
        "networkSettings": {
            "targetGoogleSearch": True,
            "targetSearchNetwork": True,
            "targetContentNetwork": False,
            "targetPartnerSearchNetwork": False,
        },
        "startDate": start,
    }
    if end:
        create["endDate"] = end

    result = _mutate("campaigns", customer_id, headers, [{"create": create}])
    return result["results"][0]["resourceName"]


def _create_ad_group(customer_id, headers, campaign, campaign_resource):
    operations = [
        {
            "create": {
                "name": campaign.ad_group_name,
                "campaign": campaign_resource,
                "type": "SEARCH_STANDARD",
                "status": "ENABLED",
                "cpcBidMicros": "1000000",  # 1.00 in account currency; unused while paused
            }
        }
    ]
    result = _mutate("adGroups", customer_id, headers, operations)
    return result["results"][0]["resourceName"]


def _create_responsive_search_ad(customer_id, headers, campaign, ad_group_resource):
    operations = [
        {
            "create": {
                "adGroup": ad_group_resource,
                # Ad also created PAUSED — belt-and-suspenders on top of the paused campaign.
                "status": "PAUSED",
                "ad": {
                    "finalUrls": [_final_url(campaign)],
                    "responsiveSearchAd": {
                        "headlines": [{"text": t} for t in _headlines(campaign)],
                        "descriptions": [{"text": t} for t in _descriptions(campaign)],
                    },
                },
            }
        }
    ]
    _mutate("adGroupAds", customer_id, headers, operations)


# --------------------------------------------------------------------------- #
# REST plumbing: config, OAuth, mutate, errors.
# --------------------------------------------------------------------------- #
def _rest_context():
    """Return (customer_id, request_headers) ready for Google Ads REST calls."""
    config = _load_config()

    customer_id = (os.getenv("GOOGLE_ADS_CUSTOMER_ID") or "").replace("-", "").strip()
    if not customer_id:
        raise GoogleAdsError("GOOGLE_ADS_CUSTOMER_ID is not set in .env")

    access_token = _fetch_access_token(config)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "developer-token": str(config["developer_token"]),
        "login-customer-id": str(config["login_customer_id"]).replace("-", ""),
        "Content-Type": "application/json",
    }
    return customer_id, headers


def _load_config():
    """Read credentials from google-ads.yaml."""
    import yaml  # PyYAML

    if not os.path.exists(_YAML_PATH):
        raise GoogleAdsError(
            f"google-ads.yaml not found at {_YAML_PATH}. See docs/GOOGLE_ADS_SETUP.md."
        )
    with open(_YAML_PATH, "r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}

    required = ("developer_token", "client_id", "client_secret", "refresh_token", "login_customer_id")
    missing = [key for key in required if not config.get(key)]
    if missing:
        raise GoogleAdsError("google-ads.yaml is missing keys: " + ", ".join(missing))
    return config


def _fetch_access_token(config):
    """Exchange the refresh token for a short-lived OAuth access token."""
    import requests

    try:
        response = requests.post(
            _TOKEN_URL,
            data={
                "client_id": config["client_id"],
                "client_secret": config["client_secret"],
                "refresh_token": config["refresh_token"],
                "grant_type": "refresh_token",
            },
            timeout=30,
        )
    except requests.RequestException as exc:
        raise GoogleAdsError(f"Network error during OAuth token request: {exc}") from exc

    if not response.ok:
        raise GoogleAdsError(
            f"OAuth token request failed (HTTP {response.status_code}): {response.text[:300]}"
        )
    token = response.json().get("access_token")
    if not token:
        raise GoogleAdsError("OAuth token response did not include an access_token")
    return token


def _mutate(resource, customer_id, headers, operations):
    """POST a list of operations to a Google Ads `...:mutate` REST endpoint."""
    import requests

    url = f"{_BASE_URL}/customers/{customer_id}/{resource}:mutate"
    try:
        response = requests.post(url, headers=headers, json={"operations": operations}, timeout=60)
    except requests.RequestException as exc:
        raise GoogleAdsError(f"Network error calling Google Ads: {exc}") from exc

    if not response.ok:
        raise GoogleAdsError(_format_rest_error(response))
    return response.json()


def _format_rest_error(response):
    """Turn a Google Ads REST error body into a short, readable message."""
    try:
        error = response.json().get("error", {})
        messages = []
        for detail in error.get("details", []):
            for item in detail.get("errors", []):
                if item.get("message"):
                    messages.append(item["message"])
        if messages:
            return "Google Ads API error: " + "; ".join(messages)
        if error.get("message"):
            return "Google Ads API error: " + error["message"]
    except ValueError:
        pass
    return f"Google Ads API error: HTTP {response.status_code} {response.text[:300]}"


# --------------------------------------------------------------------------- #
# Helpers (no Google dependency).
# --------------------------------------------------------------------------- #
def _campaign_dates(campaign):
    """Return (start, end) as YYYYMMDD strings; push past start dates to tomorrow."""
    tomorrow = date.today() + timedelta(days=1)
    start = campaign.start_date or tomorrow
    if start < tomorrow:
        start = tomorrow
    end = campaign.end_date
    if end and end < start:
        end = None  # start was pushed past the original end; let it run open-ended
    return start.strftime("%Y%m%d"), (end.strftime("%Y%m%d") if end else None)


def _final_url(campaign):
    """Final URL for the ad. Google requires a scheme, so add https:// if missing."""
    url = (campaign.asset_url or "").strip()
    if not url:
        return "https://www.example.com"
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def _dedupe_truncate(values, max_len):
    out, seen = [], set()
    for value in values:
        text = (value or "").strip()[:max_len].strip()
        key = text.lower()
        if text and key not in seen:
            out.append(text)
            seen.add(key)
    return out


def _headlines(campaign):
    """RSAs require >=3 unique headlines, each <=30 chars (Google allows up to 15)."""
    candidates = [
        campaign.ad_headline,
        campaign.name,
        campaign.ad_group_name,
        campaign.objective,
        "Learn More",
        "Get Started Today",
    ]
    headlines = _dedupe_truncate(candidates, _HEADLINE_MAX)
    base = (campaign.ad_headline or "Ad").strip()[: _HEADLINE_MAX - 3]
    i = 1
    while len(headlines) < _MIN_HEADLINES:
        filler = f"{base} {i}".strip()[:_HEADLINE_MAX]
        if filler.lower() not in {h.lower() for h in headlines}:
            headlines.append(filler)
        i += 1
    return headlines[:15]


def _descriptions(campaign):
    """RSAs require >=2 unique descriptions, each <=90 chars (Google allows up to 4)."""
    candidates = [
        campaign.ad_description,
        f"{campaign.objective} - {campaign.name}",
        "Visit our website to learn more.",
    ]
    descriptions = _dedupe_truncate(candidates, _DESCRIPTION_MAX)
    base = (campaign.ad_description or "Learn more").strip()[: _DESCRIPTION_MAX - 3]
    i = 1
    while len(descriptions) < _MIN_DESCRIPTIONS:
        filler = f"{base} {i}".strip()[:_DESCRIPTION_MAX]
        if filler.lower() not in {d.lower() for d in descriptions}:
            descriptions.append(filler)
        i += 1
    return descriptions[:4]
