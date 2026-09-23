import re
from flask import render_template, request, redirect, url_for, flash
from utils.auth import login_required, current_user

from blueprints.goals import goals_bp
from models.db import goals_collection, users_collection
from services.stats_service import get_user_goals


@goals_bp.route("/goal", methods=["GET", "POST"])
@login_required
def goal():
    if request.method == "POST":
        category = request.form.get("category", "Daily")
        actions = request.form.getlist("action_name")
        targets = request.form.getlist("target_value")
        target_days_list = request.form.getlist("target_days")
        goals = []

        for action, target, td in zip(actions, targets, target_days_list):
            action = (action or "").strip()
            if not action:
                continue
            parsed_days = int(td) if td and td.isdigit() else None
            if not parsed_days:
                match = re.search(r"\d+", target or "")
                parsed_days = int(match.group(0)) if match else 21
            goals.append({
                "action": action,
                "target": (target or "").strip(),
                "target_days": parsed_days,
            })

        if not goals:
            flash("Please add at least one goal.", "error")
            return render_template("goal_setup.html", category=category)

        goals_collection.update_one(
            {"user_id": current_user.id},
            {"$set": {
                "user_id": current_user.id,
                "category": category,
                "goals": goals,
            }},
            upsert=True,
        )
        flash("Goals saved successfully.", "success")
        if request.args.get("onboarding") or request.form.get("onboarding"):
            users_collection.update_one(
                {"_id": current_user.doc["_id"]},
                {"$set": {"onboarding_complete": True}},
            )
        return redirect(url_for("checkin.checkin"))

    category = request.args.get("category", "Daily")
    return render_template("goal_setup.html", category=category)


@goals_bp.route("/home")
@login_required
def home():
    goals = get_user_goals(current_user.id)
    return render_template("home.html", has_goals=bool(goals.get("goals")))
