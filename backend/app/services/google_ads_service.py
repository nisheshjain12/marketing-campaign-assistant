"""
Google Ads integration.

Publishes a local campaign as a real **Search** campaign (created PAUSED so the
account is never charged) and pauses a campaign by its Google campaign ID.

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
# simple Campaign.start_date / end_date fields (v23+ renamed them to *_date_time).
_API_VERSION = "v22"

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


# --------------------------------------------------------------------------- #
# Offline mock.
# --------------------------------------------------------------------------- #
def _mock_publish(campaign: Campaign) -> str:
    _ = campaign  # same fields would be sent to Google Ads in production
    return str(random.randint(1_000_000_000, 9_999_999_999))


def _mock_pause(google_campaign_id: str) -> None:
    _ = google_campaign_id


# --------------------------------------------------------------------------- #
# Real Google Ads implementation.
# --------------------------------------------------------------------------- #
def _load_client():
    """Build a GoogleAdsClient from google-ads.yaml and return (client, customer_id)."""
    try:
        from google.ads.googleads.client import GoogleAdsClient
    except ImportError as exc:
        raise GoogleAdsError(
            "google-ads library is not installed. Run: pip install -r requirements.txt"
        ) from exc

    if not os.path.exists(_YAML_PATH):
        raise GoogleAdsError(
            f"google-ads.yaml not found at {_YAML_PATH}. See docs/GOOGLE_ADS_SETUP.md."
        )

    customer_id = (os.getenv("GOOGLE_ADS_CUSTOMER_ID") or "").replace("-", "").strip()
    if not customer_id:
        raise GoogleAdsError("GOOGLE_ADS_CUSTOMER_ID is not set in .env")

    try:
        client = GoogleAdsClient.load_from_storage(_YAML_PATH, version=_API_VERSION)
    except Exception as exc:  # noqa: BLE001
        raise GoogleAdsError(f"Failed to load Google Ads credentials: {exc}") from exc

    return client, customer_id


def _real_publish(campaign: Campaign) -> str:
    client, customer_id = _load_client()

    # Unique suffix so re-runs never collide on budget/campaign names.
    unique = uuid.uuid4().hex[:8]

    try:
        budget_resource = _create_budget(client, customer_id, campaign, unique)
        campaign_resource, google_campaign_id = _create_campaign(
            client, customer_id, campaign, budget_resource, unique
        )
        ad_group_resource = _create_ad_group(
            client, customer_id, campaign, campaign_resource
        )
        _create_responsive_search_ad(client, customer_id, campaign, ad_group_resource)
    except GoogleAdsError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise GoogleAdsError(_format_google_error(exc)) from exc

    return google_campaign_id


def _create_budget(client, customer_id, campaign, unique):
    budget_service = client.get_service("CampaignBudgetService")
    operation = client.get_type("CampaignBudgetOperation")
    budget = operation.create
    budget.name = f"{campaign.name} Budget {unique}"
    budget.amount_micros = int(campaign.daily_budget) * 1_000_000
    budget.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
    budget.explicitly_shared = False
    response = budget_service.mutate_campaign_budgets(
        customer_id=customer_id, operations=[operation]
    )
    return response.results[0].resource_name


def _create_campaign(client, customer_id, campaign, budget_resource, unique):
    campaign_service = client.get_service("CampaignService")
    operation = client.get_type("CampaignOperation")
    new_campaign = operation.create
    new_campaign.name = f"{campaign.name} [{unique}]"
    new_campaign.advertising_channel_type = (
        client.enums.AdvertisingChannelTypeEnum.SEARCH
    )
    # PAUSED so the campaign never serves and the account is never charged.
    new_campaign.status = client.enums.CampaignStatusEnum.PAUSED
    # Required since v22: declare the campaign carries no EU political advertising.
    new_campaign.contains_eu_political_advertising = (
        client.enums.EuPoliticalAdvertisingStatusEnum.DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING
    )
    new_campaign.manual_cpc.enhanced_cpc_enabled = False
    new_campaign.campaign_budget = budget_resource
    new_campaign.network_settings.target_google_search = True
    new_campaign.network_settings.target_search_network = True
    new_campaign.network_settings.target_content_network = False
    new_campaign.network_settings.target_partner_search_network = False

    start, end = _campaign_dates(campaign)
    new_campaign.start_date = start
    if end:
        new_campaign.end_date = end

    response = campaign_service.mutate_campaigns(
        customer_id=customer_id, operations=[operation]
    )
    resource_name = response.results[0].resource_name
    google_campaign_id = resource_name.split("/")[-1]
    return resource_name, google_campaign_id


def _create_ad_group(client, customer_id, campaign, campaign_resource):
    ad_group_service = client.get_service("AdGroupService")
    operation = client.get_type("AdGroupOperation")
    ad_group = operation.create
    ad_group.name = campaign.ad_group_name
    ad_group.campaign = campaign_resource
    ad_group.type_ = client.enums.AdGroupTypeEnum.SEARCH_STANDARD
    ad_group.status = client.enums.AdGroupStatusEnum.ENABLED
    ad_group.cpc_bid_micros = 1_000_000  # 1.00 in account currency; unused while paused
    response = ad_group_service.mutate_ad_groups(
        customer_id=customer_id, operations=[operation]
    )
    return response.results[0].resource_name


def _create_responsive_search_ad(client, customer_id, campaign, ad_group_resource):
    ad_service = client.get_service("AdGroupAdService")
    operation = client.get_type("AdGroupAdOperation")
    ad_group_ad = operation.create
    ad_group_ad.ad_group = ad_group_resource
    # Ad also created PAUSED — belt-and-suspenders on top of the paused campaign.
    ad_group_ad.status = client.enums.AdGroupAdStatusEnum.PAUSED
    ad_group_ad.ad.final_urls.append(_final_url(campaign))

    rsa = ad_group_ad.ad.responsive_search_ad
    for text in _headlines(campaign):
        asset = client.get_type("AdTextAsset")
        asset.text = text
        rsa.headlines.append(asset)
    for text in _descriptions(campaign):
        asset = client.get_type("AdTextAsset")
        asset.text = text
        rsa.descriptions.append(asset)

    ad_service.mutate_ad_group_ads(customer_id=customer_id, operations=[operation])


def _real_pause(google_campaign_id: str) -> None:
    from google.api_core import protobuf_helpers

    client, customer_id = _load_client()
    campaign_service = client.get_service("CampaignService")
    operation = client.get_type("CampaignOperation")
    update = operation.update
    update.resource_name = campaign_service.campaign_path(
        customer_id, google_campaign_id
    )
    update.status = client.enums.CampaignStatusEnum.PAUSED
    client.copy_from(
        operation.update_mask,
        protobuf_helpers.field_mask(None, update._pb),
    )
    try:
        campaign_service.mutate_campaigns(
            customer_id=customer_id, operations=[operation]
        )
    except Exception as exc:  # noqa: BLE001
        raise GoogleAdsError(_format_google_error(exc)) from exc


# --------------------------------------------------------------------------- #
# Helpers.
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
    url = (campaign.asset_url or "").strip()
    return url or "https://www.example.com"


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


def _format_google_error(exc):
    """Turn a GoogleAdsException into a short, readable message."""
    failure = getattr(exc, "failure", None)
    if failure is not None:
        messages = [error.message for error in failure.errors if error.message]
        if messages:
            return "Google Ads API error: " + "; ".join(messages)
    return f"Google Ads API error: {exc}"
