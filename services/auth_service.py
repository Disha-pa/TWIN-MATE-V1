from datetime import datetime, timedelta
import hashlib
import secrets

from pymongo.errors import DuplicateKeyError

from models.db import users_collection
from models.user import User
from utils.auth import hash_password, normalize_email, verify_password
from utils.helpers import AVATAR_COLORS

RESET_TOKEN_HOURS = 1


def create_account(email_raw, password):
    email = normalize_email(email_raw)
    if not email:
        return None, "Enter a valid email like name@gmail.com."
    if not password or len(password) < 6:
        return None, "Password must be at least 6 characters."

    if users_collection.find_one({"email": email}):
        return None, "This email is already registered. Please log in."

    try:
        result = users_collection.insert_one({
            "email": email,
            "password": hash_password(password),
            "name": "",
            "avatar_color": AVATAR_COLORS[hash(email) % len(AVATAR_COLORS)],
            "timezone": "UTC",
            "onboarding_complete": True,
            "reminder_time": "20:00",
            "created_at": datetime.utcnow(),
        })
    except DuplicateKeyError:
        return None, "This email is already registered. Please log in."

    doc = users_collection.find_one({"_id": result.inserted_id})
    return User(doc), None


def authenticate(email_raw, password):
    email = normalize_email(email_raw)
    if not email or not password:
        return None, "Enter your email and password."

    doc = users_collection.find_one({"email": email})
    if not doc or not verify_password(doc.get("password"), password):
        return None, "Invalid email or password."

    return User(doc), None


def _hash_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_password_reset_token(email_raw):
    """
    Create a one-time reset token for the email.
    Returns (raw_token_or_None, public_message).
    """
    email = normalize_email(email_raw)
    public_msg = "If that email is registered, a reset link is ready."

    if not email:
        return None, "Enter a valid email like name@gmail.com."

    doc = users_collection.find_one({"email": email})
    if not doc:
        return None, public_msg

    raw_token = secrets.token_urlsafe(32)
    users_collection.update_one(
        {"_id": doc["_id"]},
        {"$set": {
            "reset_token_hash": _hash_token(raw_token),
            "reset_token_expires": datetime.utcnow() + timedelta(hours=RESET_TOKEN_HOURS),
        }},
    )
    return raw_token, public_msg


def reset_password_with_token(token, new_password):
    if not token:
        return False, "Invalid or expired reset link."
    if not new_password or len(new_password) < 6:
        return False, "Password must be at least 6 characters."

    doc = users_collection.find_one({
        "reset_token_hash": _hash_token(token),
        "reset_token_expires": {"$gt": datetime.utcnow()},
    })
    if not doc:
        return False, "Invalid or expired reset link. Request a new one."

    users_collection.update_one(
        {"_id": doc["_id"]},
        {
            "$set": {"password": hash_password(new_password)},
            "$unset": {"reset_token_hash": "", "reset_token_expires": ""},
        },
    )
    return True, "Password updated. You can log in now."
