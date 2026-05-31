"""create campaigns table

Revision ID: 001
Revises:
Create Date: 2026-05-30

"""

from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "campaigns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("objective", sa.String(length=50), nullable=False),
        sa.Column("campaign_type", sa.String(length=50), nullable=False),
        sa.Column("daily_budget", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("google_campaign_id", sa.String(length=50), nullable=True),
        sa.Column("ad_group_name", sa.String(length=255), nullable=False),
        sa.Column("ad_headline", sa.String(length=255), nullable=False),
        sa.Column("ad_description", sa.Text(), nullable=False),
        sa.Column("asset_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("campaigns")
