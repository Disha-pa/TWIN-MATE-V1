import os
from datetime import datetime

from bson import ObjectId
from flask import Flask, render_template, session
from flask_login import current_user

from config import config_by_name
from extensions import csrf, limiter, login_manager
import models.db as database
from models.db import init_db
from models.user import User
from utils.auth import apply_auth_cookie, read_auth_cookie_user_id


def create_app(config_name=None):
    config_name = config_name or os.getenv("FLASK_ENV", "development")
    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name["development"]))

    init_db(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    if not app.config.get("RATELIMIT_ENABLED", True):
        app.config["RATELIMIT_ENABLED"] = False

    login_manager.login_view = "auth.login"
    login_manager.login_message = None
    login_manager.session_protection = app.config.get("SESSION_PROTECTION")

    @login_manager.user_loader
    def load_user(user_id):
        # Always read via module attribute — a direct import is None before init_db.
        try:
            doc = database.users_collection.find_one({"_id": ObjectId(str(user_id))})
        except Exception:
            return None
        return User(doc) if doc else None

    @login_manager.request_loader
    def load_user_from_request(req):
        """Backup auth when the Flask session cookie does not stick."""
        user_id = read_auth_cookie_user_id()
        if not user_id:
            return None
        try:
            doc = database.users_collection.find_one({"_id": ObjectId(str(user_id))})
        except Exception:
            return None
        return User(doc) if doc else None

    from blueprints.auth import auth_bp
    from blueprints.goals import goals_bp
    from blueprints.dashboard import dashboard_bp
    from blueprints.chat import chat_bp
    from blueprints.checkin import checkin_bp
    from blueprints.profile import profile_bp
    from blueprints.onboarding import onboarding_bp
    from blueprints.api import api_bp

    import blueprints.auth.routes  # noqa: F401
    import blueprints.goals.routes  # noqa: F401
    import blueprints.dashboard.routes  # noqa: F401
    import blueprints.chat.routes  # noqa: F401
    import blueprints.checkin.routes  # noqa: F401
    import blueprints.profile.routes  # noqa: F401
    import blueprints.onboarding.routes  # noqa: F401
    import blueprints.api.routes  # noqa: F401

    app.register_blueprint(auth_bp)
    app.register_blueprint(goals_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(checkin_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(onboarding_bp)
    app.register_blueprint(api_bp)
    csrf.exempt(api_bp)

    @app.route("/")
    def landing():
        return render_template("landing.html")

    if app.config.get("SCHEDULER_ENABLED") and not app.config.get("TESTING"):
        _init_scheduler(app)

    @app.before_request
    def prepare_session():
        session.permanent = True

    @app.after_request
    def attach_auth_cookie(response):
        return apply_auth_cookie(response)

    @app.context_processor
    def inject_globals():
        return {
            "current_user": current_user,
            "now_year": datetime.now().year,
        }

    return app


def _init_scheduler(app):
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from services.notification_service import run_daily_reminders

        scheduler = BackgroundScheduler(daemon=True)

        @scheduler.scheduled_job("cron", minute="*")
        def reminder_job():
            with app.app_context():
                run_daily_reminders()

        scheduler.start()
    except Exception:
        pass


app = create_app(os.getenv("FLASK_ENV", "development"))

if __name__ == "__main__":
    # use_reloader=False is REQUIRED — the reloader breaks login cookies on Windows
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=True, use_reloader=False)
