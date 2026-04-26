"""Global Flask error handlers."""
from __future__ import annotations

from flask import Flask, jsonify, redirect, request, session, url_for
from pydantic import ValidationError


class AppError(Exception):
    """Base application error."""

    status_code = 400
    error_code = "app_error"

    def __init__(self, message: str, *, status_code: int | None = None, error_code: str | None = None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        if error_code is not None:
            self.error_code = error_code


class AuthError(AppError):
    status_code = 401
    error_code = "auth_error"


class ForbiddenError(AppError):
    status_code = 403
    error_code = "forbidden"


class NotFoundError(AppError):
    status_code = 404
    error_code = "not_found"


class ConflictError(AppError):
    status_code = 409
    error_code = "conflict"


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(AppError)
    def handle_app_error(err: AppError):
        if _is_api_request():
            return jsonify({
                "success": False,
                "error": {"code": err.error_code, "message": err.message},
            }), err.status_code
        # HTML request with expired/invalid session → clear + redirect to login
        if isinstance(err, AuthError):
            session.clear()
            return redirect(url_for("auth.login_page"))
        return err.message, err.status_code

    @app.errorhandler(ValidationError)
    def handle_validation(err: ValidationError):
        return jsonify({
            "success": False,
            "error": {"code": "validation_error", "message": "Invalid input", "details": err.errors()},
        }), 422

    @app.errorhandler(404)
    def handle_404(_err):
        if _is_api_request():
            return jsonify({"success": False, "error": {"code": "not_found", "message": "Resource not found"}}), 404
        return "Not found", 404

    @app.errorhandler(500)
    def handle_500(_err):
        app.logger.exception("Internal server error")
        if _is_api_request():
            return jsonify({"success": False, "error": {"code": "internal_error", "message": "Internal server error"}}), 500
        return "Internal server error", 500


def _is_api_request() -> bool:
    return (
        "/api/" in request.path
        or request.path.startswith("/auth/api")
        or request.accept_mimetypes.best == "application/json"
        or request.is_json
    )
