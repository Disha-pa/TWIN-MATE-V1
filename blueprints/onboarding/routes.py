from flask import render_template, request, redirect, url_for, flash
from utils.auth import login_required, current_user

from blueprints.onboarding import onboarding_bp
from models.db import users_collection
from utils.helpers import sanitize_text


@onboarding_bp.route("/onboarding", methods=["GET", "POST"])
@login_required
def wizard():
    step = request.args.get("step", type=int) or 1

    if request.method == "POST":
        current_step = int(request.form.get("step", 1))

        if request.form.get("skip"):
            users_collection.update_one(
                {"_id": current_user.doc["_id"]},
                {"$set": {"onboarding_complete": True}},
            )
            flash("You can set your name and goals anytime from Home.", "success")
            return redirect(url_for("goals.home"))

        if current_step == 1:
            name = sanitize_text(request.form.get("name"), 80)
            if not name:
                flash("Please enter your name.", "error")
                return render_template("onboarding.html", step=1, user=current_user)
            users_collection.update_one(
                {"_id": current_user.doc["_id"]},
                {"$set": {"name": name}},
            )
            return redirect(url_for("onboarding.wizard", step=2))
        if current_step == 2:
            category = request.form.get("category", "Daily")
            return redirect(url_for("goals.goal", category=category, onboarding=1))

    if current_user.onboarding_complete:
        return redirect(url_for("goals.home"))

    return render_template("onboarding.html", step=step, user=current_user)
