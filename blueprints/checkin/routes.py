from flask import render_template, request, redirect, url_for, flash
from utils.auth import login_required, current_user

from blueprints.checkin import checkin_bp
from services.stats_service import get_user_goals, get_today_checkin, save_checkin
from utils.helpers import sanitize_text


@checkin_bp.route("/checkin", methods=["GET", "POST"])
@login_required
def checkin():
    goals = get_user_goals(current_user.id)
    goal_list = goals.get("goals", [])
    if not goal_list:
        flash("Set your goals first to start daily check-ins.", "error")
        return redirect(url_for("goals.home"))

    today_doc = get_today_checkin(current_user.id)

    if request.method == "POST":
        statuses = {}
        for g in goal_list:
            action = g["action"]
            value = request.form.get(f"status__{action}", "")
            if value in ("done", "not_done"):
                statuses[action] = value

        energy = request.form.get("energy")
        mood = request.form.get("mood")
        note = sanitize_text(request.form.get("note"), 500)

        if not statuses:
            flash("Mark at least one goal for today.", "error")
        else:
            save_checkin(current_user.id, statuses, energy=energy, mood=mood, note=note)
            flash("Check-in saved. Great job showing up today!", "success")
            return redirect(url_for("dashboard.dashboard"))

    return render_template(
        "checkin.html",
        goals=goals,
        today_checkin=today_doc,
        already_checked_in=bool(today_doc and today_doc.get("statuses")),
    )
