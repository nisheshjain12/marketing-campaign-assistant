"""Application-level errors and Flask error handlers."""

from flask import jsonify


class ValidationError(Exception):
    """Raised when request data fails business or format rules."""

    def __init__(self, message, details=None):
        super().__init__(message)
        self.message = message
        self.details = details or []


class NotFoundError(Exception):
    """Raised when a campaign ID does not exist in the local database."""

    def __init__(self, message="Campaign not found"):
        super().__init__(message)
        self.message = message


class GoogleAdsError(Exception):
    """Raised when the Google Ads API returns an error."""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


def register_error_handlers(app):
    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        return jsonify(
            {
                "error": {
                    "message": error.message,
                    "details": error.details,
                }
            }
        ), 400

    @app.errorhandler(NotFoundError)
    def handle_not_found_error(error):
        return jsonify({"error": {"message": error.message}}), 404

    @app.errorhandler(GoogleAdsError)
    def handle_google_ads_error(error):
        return jsonify({"error": {"message": error.message}}), 502

    @app.errorhandler(404)
    def handle_not_found(error):
        return jsonify({"error": {"message": "Resource not found"}}), 404
