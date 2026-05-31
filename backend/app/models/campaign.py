import uuid
from datetime import date, datetime, timezone

from app.extensions import db


def _utc_now():
    return datetime.now(timezone.utc)


class Campaign(db.Model):
    """Local copy of a marketing campaign (before / after Google Ads publish)."""

    __tablename__ = "campaigns"

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(255), nullable=False)
    objective = db.Column(db.String(50), nullable=False)
    campaign_type = db.Column(db.String(50), nullable=False, default="SEARCH")
    daily_budget = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="DRAFT")
    google_campaign_id = db.Column(db.String(50), nullable=True)
    ad_group_name = db.Column(db.String(255), nullable=False)
    ad_headline = db.Column(db.String(255), nullable=False)
    ad_description = db.Column(db.Text, nullable=False)
    asset_url = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now)

    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "objective": self.objective,
            "campaign_type": self.campaign_type,
            "daily_budget": self.daily_budget,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "status": self.status,
            "google_campaign_id": self.google_campaign_id,
            "ad_group_name": self.ad_group_name,
            "ad_headline": self.ad_headline,
            "ad_description": self.ad_description,
            "asset_url": self.asset_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
