from flask import jsonify

from app.routes import api_bp


@api_bp.route("/health", methods=["GET"])
def health_check():
    return jsonify({"data": {"status": "ok"}}), 200
