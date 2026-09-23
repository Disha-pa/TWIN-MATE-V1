from datetime import datetime
from flask import render_template, request, redirect, url_for, flash
from utils.auth import login_required, current_user

from blueprints.dashboard import dashboard_bp
from models.db import users_collection
from services.stats_service import build_dashboard_stats, save_checkin, get_user_goals


@dashboard_bp.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    if request.method == "POST":
        reminder_time = request.form.get("reminder_time", "20:00")
        users_collection.update_one(
            {"_id": current_user.doc["_id"]},
            {"$set": {"reminder_time": reminder_time}},
        )
        flash("Reminder time saved.", "success")
        return redirect(url_for("dashboard.dashboard"))

    selected_year = request.args.get("year", type=int)
    selected_month = request.args.get("month", type=int)
    selected_date = request.args.get("selected_date")

    stats = build_dashboard_stats(
        current_user.id,
        selected_year=selected_year,
        selected_month=selected_month,
        selected_date=selected_date,
    )

    reminder_time = current_user.reminder_time or "20:00"
    reminder_banner = ""
    if reminder_time and stats.get("today_checkin") is None:
        now = datetime.now().strftime("%H:%M")
        if now >= reminder_time:
            reminder_banner = "Reminder: you haven't checked in today. Log your progress."

    return render_template(
        "dashboard.html",
        reminder_time=reminder_time,
        reminder_banner=reminder_banner,
        **stats,
    )


@dashboard_bp.route("/dashboard/week-update", methods=["POST"])
@login_required
def week_update():
    """HTMX partial update for today's goal status."""
    goals = get_user_goals(current_user.id)
    statuses = {}
    for g in goals.get("goals", []):
        action = g["action"]
        value = request.form.get(f"status__{action}", "")
        if value in ("done", "not_done"):
            statuses[action] = value
    if statuses:
        existing = build_dashboard_stats(current_user.id).get("today_checkin") or {}
        merged = {**existing.get("statuses", {}), **statuses}
        save_checkin(
            current_user.id,
            merged,
            energy=existing.get("energy"),
            mood=existing.get("mood"),
            note=existing.get("note", ""),
        )
    stats = build_dashboard_stats(current_user.id)
    return render_template(
        "partials/week_view.html",
        week_days=stats["week_days"],
        goals=stats["goals"],
        today_checkin=stats.get("today_checkin"),
    )
