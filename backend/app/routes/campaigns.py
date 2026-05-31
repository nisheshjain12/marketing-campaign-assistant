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
