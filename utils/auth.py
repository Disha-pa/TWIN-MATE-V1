"""Auth helpers + Flask-Login, with a durable signed cookie backup."""
from flask import current_app, g, request, session
from flask_login import current_user, login_required
from flask_login import login_user as _flask_login_user
from flask_login import logout_user as _flask_logout_user
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

PASSWORD_METHOD = "pbkdf2:sha256"
AUTH_COOKIE = "twin_mate_uid"
AUTH_MAX_AGE = 60 * 60 * 24 * 31  # 31 days


def normalize_email(value):
    email = (value or "").strip().lower()
    if not email or "@" not in email:
        return ""
    local, _, domain = email.partition("@")
    if not local or "." not in domain:
        return ""
    return email


def hash_password(password):
    return generate_password_hash(password, method=PASSWORD_METHOD)


def verify_password(stored_hash, password):
    if not stored_hash or not password:
        return False
    try:
        return check_password_hash(stored_hash, password)
    except Exception:
        return False


def _signer():
    return URLSafeTimedSerializer(
        current_app.config["SECRET_KEY"],
        salt="twin-mate-uid-v1",
    )


def login_user(user, remember=True):
    """Flask-Login session + signed cookie so other pages stay logged in."""
    session.permanent = True
    _flask_login_user(user, remember=remember)
    session.modified = True
    g.set_auth_cookie = str(user.id)
    g.clear_auth_cookie = False


def logout_user():
    _flask_logout_user()
    g.clear_auth_cookie = True
    g.set_auth_cookie = None


def read_auth_cookie_user_id():
    token = request.cookies.get(AUTH_COOKIE)
    if not token:
        return None
    try:
        return str(_signer().loads(token, max_age=AUTH_MAX_AGE))
    except (BadSignature, SignatureExpired, Exception):
        return None


def apply_auth_cookie(response):
    """Attach/clear the durable auth cookie on the outgoing response."""
    if getattr(g, "clear_auth_cookie", False):
        response.set_cookie(
            AUTH_COOKIE,
            "",
            max_age=0,
            expires=0,
            path="/",
            httponly=True,
            samesite="Lax",
        )
        return response

    user_id = getattr(g, "set_auth_cookie", None)
    if user_id:
        token = _signer().dumps(str(user_id))
        response.set_cookie(
            AUTH_COOKIE,
            token,
            max_age=AUTH_MAX_AGE,
            path="/",
            httponly=True,
            samesite="Lax",
        )
    return response


__all__ = [
    "current_user",
    "login_required",
    "login_user",
    "logout_user",
    "normalize_email",
    "hash_password",
    "verify_password",
    "read_auth_cookie_user_id",
    "apply_auth_cookie",
    "AUTH_COOKIE",
]
