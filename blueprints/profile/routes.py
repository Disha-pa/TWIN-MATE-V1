import json
import os
import re
from datetime import datetime

from flask import (
    Response,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from werkzeug.utils import secure_filename

from blueprints.profile import profile_bp
from extensions import csrf
from models.db import (
    chat_messages_collection,
    checkins_collection,
    goals_collection,
    push_subscriptions_collection,
    users_collection,
)
from utils.auth import hash_password, login_required, current_user, logout_user, verify_password
from utils.helpers import sanitize_text

ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "gif", "webp"}
USERNAME_RE = re.compile(r"^[a-z0-9_]{3,20}$")


def _avatar_folder():
    folder = os.path.join(current_app.root_path, "static", "uploads", "avatars")
    os.makedirs(folder, exist_ok=True)
    return folder


def _allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXT


def _save_profile_pic(file_storage, user_id):
    if not file_storage or not file_storage.filename:
        return None, None
    if not _allowed_file(file_storage.filename):
        return None, "Use a PNG, JPG, GIF, or WEBP image."

    ext = file_storage.filename.rsplit(".", 1)[1].lower()
    filename = secure_filename(f"{user_id}.{ext}")
    path = os.path.join(_avatar_folder(), filename)
    file_storage.save(path)
    # relative path served by Flask static
    return f"uploads/avatars/{filename}", None


@profile_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        action = request.form.get("action", "update")
        if action == "update":
            name = sanitize_text(request.form.get("name"), 80)
            username = sanitize_text(request.form.get("username"), 40).lower()
            timezone = sanitize_text(request.form.get("timezone"), 40) or "UTC"
            age_raw = (request.form.get("age") or "").strip()
            remove_pic = request.form.get("remove_pic") == "1"

            age = None
            if age_raw:
                if not age_raw.isdigit():
                    flash("Age must be a number.", "error")
                    return render_template("profile.html", user=current_user)
                age = int(age_raw)
                if age < 5 or age > 120:
                    flash("Age must be between 5 and 120.", "error")
                    return render_template("profile.html", user=current_user)

            if username:
                if not USERNAME_RE.match(username):
                    flash("Username: 3–20 chars, letters/numbers/underscore only.", "error")
                    return render_template("profile.html", user=current_user)
                existing = users_collection.find_one({
                    "username": username,
                    "_id": {"$ne": current_user.doc["_id"]},
                })
                if existing:
                    flash("Username already taken.", "error")
                    return render_template("profile.html", user=current_user)

            updates = {
                "name": name,
                "username": username,
                "timezone": timezone,
                "age": age,
            }

            pic_file = request.files.get("profile_pic")
            if remove_pic:
                old = current_user.profile_pic
                if old:
                    old_path = os.path.join(current_app.root_path, "static", old.replace("/", os.sep))
                    if os.path.isfile(old_path):
                        try:
                            os.remove(old_path)
                        except OSError:
                            pass
                updates["profile_pic"] = ""
            elif pic_file and pic_file.filename:
                rel_path, err = _save_profile_pic(pic_file, current_user.id)
                if err:
                    flash(err, "error")
                    return render_template("profile.html", user=current_user)
                updates["profile_pic"] = rel_path

            users_collection.update_one(
                {"_id": current_user.doc["_id"]},
                {"$set": updates},
            )
            flash("Profile updated.", "success")
        elif action == "password":
            current_pw = request.form.get("current_password", "")
            new_pw = request.form.get("new_password", "")
            if not verify_password(current_user.doc["password"], current_pw):
                flash("Current password is incorrect.", "error")
            elif len(new_pw) < 6:
                flash("New password must be at least 6 characters.", "error")
            else:
                users_collection.update_one(
                    {"_id": current_user.doc["_id"]},
                    {"$set": {"password": hash_password(new_pw)}},
                )
                flash("Password changed.", "success")
        elif action == "delete":
            uid = current_user.id
            # remove avatar file if any
            old = current_user.profile_pic
            if old:
                old_path = os.path.join(current_app.root_path, "static", old.replace("/", os.sep))
                if os.path.isfile(old_path):
                    try:
                        os.remove(old_path)
                    except OSError:
                        pass
            users_collection.delete_one({"_id": current_user.doc["_id"]})
            goals_collection.delete_many({"user_id": uid})
            checkins_collection.delete_many({"user_id": uid})
            chat_messages_collection.delete_many({"user_id": uid})
            push_subscriptions_collection.delete_many({"user_id": uid})
            logout_user()
            flash("Account deleted.", "success")
            return redirect(url_for("landing"))
        return redirect(url_for("profile.profile"))

    return render_template("profile.html", user=current_user)


@profile_bp.route("/profile/export")
@login_required
def export_data():
    uid = current_user.id
    data = {
        "user": {
            "email": current_user.email,
            "name": current_user.name,
            "username": current_user.username,
            "age": current_user.age,
            "profile_pic": current_user.profile_pic,
        },
        "goals": goals_collection.find_one({"user_id": uid}, {"_id": 0}),
        "checkins": list(checkins_collection.find({"user_id": uid}, {"_id": 0})),
        "chat_messages": list(chat_messages_collection.find({"user_id": uid}, {"_id": 0})),
        "exported_at": datetime.utcnow().isoformat(),
    }
    return Response(
        json.dumps(data, default=str, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment;filename=twin_mate_export.json"},
    )


@profile_bp.route("/profile/push-subscribe", methods=["POST"])
@login_required
@csrf.exempt
def push_subscribe():
    subscription = request.get_json()
    if not subscription:
        return jsonify({"ok": False}), 400
    push_subscriptions_collection.update_one(
        {"user_id": current_user.id, "endpoint": subscription.get("endpoint")},
        {"$set": {
            "user_id": current_user.id,
            "subscription": subscription,
            "updated_at": datetime.utcnow(),
        }},
        upsert=True,
    )
    return jsonify({"ok": True})
