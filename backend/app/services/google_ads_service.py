"""Google Ads API integration — isolated from Flask HTTP layer."""

import uuid
from datetime import date, datetime, timedelta

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

from app.config import Config
from app.errors import GoogleAdsError
from app.models import Campaign

_START_DATE_FORMAT = "%Y%m%d 00:00:00"
_END_DATE_FORMAT = "%Y%m%d 23:59:59"
_DEFAULT_FINAL_URL = "https://www.example.com/"


def get_client() -> GoogleAdsClient:
    """
    Load the official Google Ads client from google-ads.yaml.
    Assignment requirement: GoogleAdsClient.load_from_storage()
    """
    config_path = Config.GOOGLE_ADS_CONFIG_PATH
    if not config_path:
        raise GoogleAdsError("GOOGLE_ADS_CONFIG_PATH is not configured")
    return GoogleAdsClient.load_from_storage(config_path)


def publish_search_campaign(campaign: Campaign) -> str:
    """
    Create Budget → Campaign → Ad Group → Responsive Search Ad in Google Ads.
    Campaign is created PAUSED so the account is not charged.
    Returns the numeric Google campaign ID.
    """
    customer_id = _require_customer_id()
    client = get_client()

    try:
        budget_resource = _create_campaign_budget(client, customer_id, campaign)
        campaign_resource = _create_campaign(
            client, customer_id, campaign, budget_resource
        )
        ad_group_resource = _create_ad_group(
            client, customer_id, campaign, campaign_resource
        )
        _create_responsive_search_ad(client, customer_id, campaign, ad_group_resource)
        return _resource_id(campaign_resource)
    except GoogleAdsException as exc:
        raise GoogleAdsError(_format_google_ads_error(exc)) from exc


def pause_campaign(google_campaign_id: str) -> None:
    """Set an existing Google Ads campaign to PAUSED."""
    customer_id = _require_customer_id()
    client = get_client()
    campaign_service = client.get_service("CampaignService")

    campaign_operation = client.get_type("CampaignOperation")
    campaign = campaign_operation.update
    campaign.resource_name = campaign_service.campaign_path(
        customer_id, google_campaign_id
    )
    campaign.status = client.enums.CampaignStatusEnum.PAUSED
    campaign_operation.update_mask.paths.append("status")

    try:
        campaign_service.mutate_campaigns(
            customer_id=customer_id,
            operations=[campaign_operation],
        )
    except GoogleAdsException as exc:
        raise GoogleAdsError(_format_google_ads_error(exc)) from exc


def _create_campaign_budget(client, customer_id: str, campaign: Campaign) -> str:
    service = client.get_service("CampaignBudgetService")
    operation = client.get_type("CampaignBudgetOperation")
    budget = operation.create
    budget.name = f"Budget {campaign.name} {uuid.uuid4()}"
    budget.delivery_method = client.enums.BudgetDeliveryMethodEnum.STANDARD
    budget.amount_micros = campaign.daily_budget * 1_000_000

    response = service.mutate_campaign_budgets(
        customer_id=customer_id,
        operations=[operation],
    )
    return response.results[0].resource_name


def _create_campaign(
    client, customer_id: str, campaign: Campaign, budget_resource: str
) -> str:
    service = client.get_service("CampaignService")
    operation = client.get_type("CampaignOperation")
    google_campaign = operation.create

    google_campaign.name = campaign.name
    google_campaign.advertising_channel_type = (
        client.enums.AdvertisingChannelTypeEnum.SEARCH
    )
    # Safety: PAUSED so ads do not run and spend money during testing
    google_campaign.status = client.enums.CampaignStatusEnum.PAUSED
    google_campaign.manual_cpc = client.get_type("ManualCpc")
    google_campaign.campaign_budget = budget_resource

    google_campaign.network_settings.target_google_search = True
    google_campaign.network_settings.target_search_network = True
    google_campaign.network_settings.target_partner_search_network = False
    google_campaign.network_settings.target_content_network = False

    google_campaign.contains_eu_political_advertising = (
        client.enums.EuPoliticalAdvertisingStatusEnum.DOES_NOT_CONTAIN_EU_POLITICAL_ADVERTISING
    )

    google_campaign.start_date_time = _format_start_datetime(campaign.start_date)
    if campaign.end_date:
        google_campaign.end_date_time = _format_end_datetime(campaign.end_date)

    response = service.mutate_campaigns(
        customer_id=customer_id,
        operations=[operation],
    )
    return response.results[0].resource_name


def _create_ad_group(
    client, customer_id: str, campaign: Campaign, campaign_resource: str
) -> str:
    service = client.get_service("AdGroupService")
    operation = client.get_type("AdGroupOperation")
    ad_group = operation.create

    ad_group.name = campaign.ad_group_name
    ad_group.status = client.enums.AdGroupStatusEnum.ENABLED
    ad_group.campaign = campaign_resource
    ad_group.type_ = client.enums.AdGroupTypeEnum.SEARCH_STANDARD

    response = service.mutate_ad_groups(
        customer_id=customer_id,
        operations=[operation],
    )
    return response.results[0].resource_name


def _create_responsive_search_ad(
    client, customer_id: str, campaign: Campaign, ad_group_resource: str
) -> None:
    """
    RSA requires at least 3 headlines and 2 descriptions.
    We pad from the user's single headline/description if needed.
    """
    service = client.get_service("AdGroupAdService")
    operation = client.get_type("AdGroupAdOperation")
    ad_group_ad = operation.create

    ad_group_ad.ad_group = ad_group_resource
    ad_group_ad.status = client.enums.AdGroupAdStatusEnum.PAUSED
    ad_group_ad.ad.final_urls.append(campaign.asset_url or _DEFAULT_FINAL_URL)

    rsa = ad_group_ad.ad.responsive_search_ad
    for text in _headline_variants(campaign.ad_headline):
        asset = client.get_type("AdTextAsset")
        asset.text = text[:30]
        rsa.headlines.append(asset)

    for text in _description_variants(campaign.ad_description):
        asset = client.get_type("AdTextAsset")
        asset.text = text[:90]
        rsa.descriptions.append(asset)

    service.mutate_ad_group_ads(
        customer_id=customer_id,
        operations=[operation],
    )


def _headline_variants(headline: str) -> list[str]:
    base = headline.strip()
    return [
        base,
        f"{base} - Learn More"[:30],
        f"Shop {base}"[:30],
    ]


def _description_variants(description: str) -> list[str]:
    base = description.strip()
    return [
        base,
        f"{base} Visit us today."[:90],
    ]


def _format_start_datetime(start_date: date) -> str:
    # Use provided date; if in the past, push to tomorrow for safety
    safe_date = start_date
    if safe_date <= date.today():
        safe_date = date.today() + timedelta(days=1)
    return datetime.combine(safe_date, datetime.min.time()).strftime(_START_DATE_FORMAT)


def _format_end_datetime(end_date: date) -> str:
    return datetime.combine(end_date, datetime.min.time()).strftime(_END_DATE_FORMAT)


def _resource_id(resource_name: str) -> str:
    return resource_name.split("/")[-1]


def _require_customer_id() -> str:
    customer_id = Config.GOOGLE_ADS_CUSTOMER_ID.replace("-", "").strip()
    if not customer_id:
        raise GoogleAdsError(
            "GOOGLE_ADS_CUSTOMER_ID is not set in .env "
            "(client account ID, numbers only)"
        )
    return customer_id


def _format_google_ads_error(exc: GoogleAdsException) -> str:
    messages = [error.message for error in exc.failure.errors]
    if messages:
        return "; ".join(messages)
    return str(exc)
