"""MARAMARA - Flask application factory.

Therapeutic Speech Intelligence Platform.
Serves both REST API (for mobile) and HTML dashboard (for therapist).
"""
from __future__ import annotations

import logging
from flask import Flask, render_template, redirect, url_for, session
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import get_settings
from utils.logger import configure_logging
from utils.errors import register_error_handlers
from db.supabase_client import init_supabase_client


def create_app() -> Flask:
    """Application factory pattern."""
    settings = get_settings()
    configure_logging(settings.log_level)

    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.config["SECRET_KEY"] = settings.secret_key
    app.config["DEBUG"] = settings.debug
    app.config["SETTINGS"] = settings

    CORS(
        app,
        resources={r"/api/*": {"origins": "*"}},
        supports_credentials=True,
    )

    Limiter(
        get_remote_address,
        app=app,
        default_limits=["200 per minute", "50 per second"],
        storage_uri=settings.redis_url,
    )

    init_supabase_client(settings)

    _register_blueprints(app)
    register_error_handlers(app)

    @app.route("/")
    def index():
        if "user" in session:
            role = session["user"].get("role", "user")
            if role == "therapist":
                return redirect(url_for("therapist.overview"))
            if role == "admin":
                return redirect(url_for("admin.dashboard"))
            return redirect(url_for("dashboard.home"))
        return render_template("landing.html")

    @app.route("/health")
    def health():
        return {"status": "healthy", "service": "maramara-api"}

    logging.getLogger(__name__).info(
        "MARAMARA API initialized (env=%s, debug=%s)",
        settings.app_env,
        settings.debug,
    )
    return app


def _register_blueprints(app: Flask) -> None:
    """Register all blueprints."""
    from routes.auth import bp as auth_bp
    from routes.voice import bp as voice_bp
    from routes.audio import bp as audio_bp
    from routes.dashboard import bp as dashboard_bp
    from routes.insights import bp as insights_bp
    from routes.therapist import bp as therapist_bp
    from routes.reports import bp as reports_bp
    from routes.admin import bp as admin_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(voice_bp, url_prefix="/voice")
    app.register_blueprint(audio_bp, url_prefix="/api/audio")
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")
    app.register_blueprint(insights_bp, url_prefix="/api/insights")
    app.register_blueprint(therapist_bp, url_prefix="/therapist")
    app.register_blueprint(reports_bp, url_prefix="/reports")
    app.register_blueprint(admin_bp, url_prefix="/admin")


app = create_app()


if __name__ == "__main__":
    settings = get_settings()
    app.run(host="0.0.0.0", port=5000, debug=settings.debug)
