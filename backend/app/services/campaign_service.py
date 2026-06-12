from datetime import date
from uuid import UUID

from app.errors import NotFoundError, ValidationError
from app.extensions import db
from app.models import Campaign
from app.services import google_ads_service

REQUIRED_FIELDS = (
    "name",
    "objective",
    "daily_budget",
    "start_date",
    "ad_group_name",
    "ad_headline",
    "ad_description",
)


def _is_missing(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def create_campaign(payload: dict) -> Campaign:
    """Validate input and persist a new campaign with status DRAFT."""
    if not isinstance(payload, dict):
        raise ValidationError("Request body must be a JSON object")

    missing = [field for field in REQUIRED_FIELDS if _is_missing(payload.get(field))]
    if missing:
        raise ValidationError(
            "Missing required fields",
            details=[f"{field} is required" for field in missing],
        )

    daily_budget = _parse_positive_int(payload.get("daily_budget"), "daily_budget")
    start_date = _parse_date(payload.get("start_date"), "start_date")
    end_date = _parse_optional_date(payload.get("end_date"), "end_date")

    if end_date and end_date < start_date:
        raise ValidationError(
            "Invalid date range",
            details=["end_date must be on or after start_date"],
        )

    campaign = Campaign(
        name=str(payload["name"]).strip(),
        objective=str(payload["objective"]).strip(),
        campaign_type=str(payload.get("campaign_type") or "SEARCH").strip(),
        daily_budget=daily_budget,
        start_date=start_date,
        end_date=end_date,
        status="DRAFT",
        ad_group_name=str(payload["ad_group_name"]).strip(),
        ad_headline=str(payload["ad_headline"]).strip(),
        ad_description=str(payload["ad_description"]).strip(),
        asset_url=_optional_string(payload.get("asset_url")),
    )

    if not campaign.name:
        raise ValidationError("Invalid name", details=["name cannot be empty"])

    db.session.add(campaign)
    db.session.commit()
    return campaign


def list_campaigns() -> list[Campaign]:
    """Return all campaigns, newest first."""
    return Campaign.query.order_by(Campaign.created_at.desc()).all()


def get_campaign(campaign_id: str) -> Campaign:
    """Load one campaign by UUID or raise NotFoundError."""
    campaign = db.session.get(Campaign, _parse_uuid(campaign_id))
    if campaign is None:
        raise NotFoundError(f"Campaign not found: {campaign_id}")
    return campaign


def publish_campaign(campaign_id: str) -> Campaign:
    """Publish a local DRAFT campaign to Google Ads."""
    campaign = get_campaign(campaign_id)

    if campaign.status == "PUBLISHED":
        raise ValidationError(
            "Campaign already published",
            details=["This campaign has already been sent to Google Ads"],
        )

    if campaign.campaign_type.upper() != "SEARCH":
        raise ValidationError(
            "Unsupported campaign type",
            details=["Only SEARCH campaigns are supported in this version"],
        )

    google_campaign_id = google_ads_service.publish_search_campaign(campaign)

    campaign.google_campaign_id = google_campaign_id
    campaign.status = "PUBLISHED"
    db.session.commit()
    return campaign


def pause_campaign(campaign_id: str) -> Campaign:
    """Pause a published campaign in Google Ads and update local status."""
    campaign = get_campaign(campaign_id)

    if not campaign.google_campaign_id:
        raise ValidationError(
            "Campaign is not published",
            details=["Publish the campaign before trying to pause it"],
        )

    if campaign.status == "PAUSED":
        raise ValidationError(
            "Campaign already paused",
            details=["This campaign is already paused"],
        )

    google_ads_service.pause_campaign(campaign.google_campaign_id)

    campaign.status = "PAUSED"
    db.session.commit()
    return campaign


def resume_campaign(campaign_id: str) -> Campaign:
    """Resume (enable) a paused campaign in Google Ads and update local status."""
    campaign = get_campaign(campaign_id)

    if not campaign.google_campaign_id:
        raise ValidationError(
            "Campaign is not published",
            details=["Publish the campaign before trying to resume it"],
        )

    if campaign.status != "PAUSED":
        raise ValidationError(
            "Campaign is not paused",
            details=["Only paused campaigns can be resumed"],
        )

    google_ads_service.resume_campaign(campaign.google_campaign_id)

    campaign.status = "PUBLISHED"
    db.session.commit()
    return campaign


def _parse_uuid(value: str) -> UUID:
    try:
        return UUID(str(value))
    except (TypeError, ValueError):
        raise NotFoundError(f"Campaign not found: {value}")


def _parse_positive_int(value, field_name: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValidationError(
            f"Invalid {field_name}",
            details=[f"{field_name} must be a positive integer"],
        )
    if number <= 0:
        raise ValidationError(
            f"Invalid {field_name}",
            details=[f"{field_name} must be greater than 0"],
        )
    return number


def _parse_date(value, field_name: str) -> date:
    if not value:
        raise ValidationError(
            f"Invalid {field_name}",
            details=[f"{field_name} must be a date string (YYYY-MM-DD)"],
        )
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        raise ValidationError(
            f"Invalid {field_name}",
            details=[f"{field_name} must use format YYYY-MM-DD"],
        )


def _parse_optional_date(value, field_name: str):
    if value in (None, ""):
        return None
    return _parse_date(value, field_name)


def _optional_string(value):
    if value in (None, ""):
        return None
    return str(value).strip() or None
