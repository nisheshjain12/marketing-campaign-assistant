import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_BACKEND_DIR = Path(__file__).resolve().parent.parent


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/campaign_assistant",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

    # Google Ads — customer account where campaigns are created (no dashes)
    GOOGLE_ADS_CUSTOMER_ID = os.getenv("GOOGLE_ADS_CUSTOMER_ID", "")
    GOOGLE_ADS_CONFIG_PATH = os.getenv(
        "GOOGLE_ADS_CONFIG_PATH",
        str(_BACKEND_DIR / "google-ads.yaml"),
    )
