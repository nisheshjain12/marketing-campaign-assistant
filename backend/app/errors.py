"""Application-level errors and Flask error handlers."""

from flask import jsonify


class ValidationError(Exception):
    """Raised when request data fails business or format rules."""

    def __init__(self, message, details=None):
        super().__init__(message)
        self.message = message
        self.details = details or []


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

    @app.errorhandler(404)
    def handle_not_found(error):
        return jsonify({"error": {"message": "Resource not found"}}), 404
