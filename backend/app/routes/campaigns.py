from flask import jsonify, request

from app.routes import api_bp
from app.services import campaign_service


@api_bp.route("/campaigns", methods=["GET"])
def list_campaigns():
    """
    Return all locally saved campaigns.
    Assignment requirement: GET /api/campaigns
    """
    campaigns = campaign_service.list_campaigns()
    return jsonify({"data": [campaign.to_dict() for campaign in campaigns]}), 200


@api_bp.route("/campaigns", methods=["POST"])
def create_campaign():
    """
    Create a campaign in the local database only (status = DRAFT).
    Assignment requirement: POST /api/campaigns
    """
    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": {"message": "JSON body required"}}), 400

    campaign = campaign_service.create_campaign(payload)
    return jsonify({"data": campaign.to_dict()}), 201


@api_bp.route("/campaigns/<campaign_id>/publish", methods=["POST"])
def publish_campaign(campaign_id):
    """
    Publish a local campaign to Google Ads.
    Assignment requirement: POST /api/campaigns/<id>/publish
    """
    campaign = campaign_service.publish_campaign(campaign_id)
    return jsonify({"data": campaign.to_dict()}), 200


@api_bp.route("/campaigns/<campaign_id>/pause", methods=["POST"])
def pause_campaign(campaign_id):
    """
    Pause a published campaign in Google Ads (stops spend).
    Assignment requirement: disable campaign so account is not charged.
    """
    campaign = campaign_service.pause_campaign(campaign_id)
    return jsonify({"data": campaign.to_dict()}), 200
