"""
Mock Google Ads integration (no real API calls).

Simulates publish (budget → campaign → ad group → ad) and pause
so you can build and test the frontend without Google credentials.
"""

import random

from app.models import Campaign

# Set to False and restore real google-ads client code when you have a working test account
USE_MOCK = True


def publish_search_campaign(campaign: Campaign) -> str:
    """
    Pretend to create a Search campaign in Google Ads (PAUSED).
    Returns a fake numeric campaign ID stored in the database.
    """
    _ = campaign  # same fields would be sent to Google Ads in production
    return str(random.randint(1_000_000_000, 9_999_999_999))


def pause_campaign(google_campaign_id: str) -> None:
    """Pretend to set the Google Ads campaign status to PAUSED."""
    _ = google_campaign_id
