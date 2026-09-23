import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Always use a real secret — empty .env SECRET_KEY would break sessions.
    SECRET_KEY = os.getenv("SECRET_KEY") or "twin-mate-dev-secret-key-change-me"
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
    DB_NAME = os.getenv("DB_NAME", "TWIN_MATE_V1")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_NAME = "twin_mate_session"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_PATH = "/"
    SESSION_COOKIE_SECURE = False
    SESSION_REFRESH_EACH_REQUEST = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=31)
    REMEMBER_COOKIE_DURATION = timedelta(days=31)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = False
    # Disable IP/UA session wiping — it was logging people out between clicks.
    SESSION_PROTECTION = None
    RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    RATELIMIT_DEFAULT = "200 per hour"
    SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
    RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
    MAIL_FROM = os.getenv("MAIL_FROM", "noreply@twinmate.app")
    VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")
    VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
    VAPID_CLAIMS_EMAIL = os.getenv("VAPID_CLAIMS_EMAIL", "mailto:admin@twinmate.app")
    SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2 MB uploads


class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False
    RATELIMIT_ENABLED = False
    WTF_CSRF_ENABLED = False


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False


class TestingConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SCHEDULER_ENABLED = False
    RATELIMIT_ENABLED = False
    DB_NAME = os.getenv("TEST_DB_NAME", "TWIN_MATE_V1_TEST")


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
