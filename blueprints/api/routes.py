from flask import jsonify, request
from utils.auth import login_required, current_user

from blueprints.api import api_bp
from services.stats_service import (
    build_dashboard_stats,
    get_user_goals,
    save_checkin,
    get_today_checkin,
    get_user_context_for_ai,
)
from services.ai_service import generate_reply, save_message
from utils.helpers import sanitize_text


@api_bp.route("/dashboard")
@login_required
def api_dashboard():
    stats = build_dashboard_stats(current_user.id)
    return jsonify({
        "streak_days": stats["streak_days"],
        "weekly_completion": stats["weekly_completion"],
        "overall_completion": stats["overall_completion"],
        "level": stats["level"],
        "badges": stats["badges"],
        "goal_progress": stats["goal_progress"],
        "focus_tip": stats["focus_tip"],
        "chart_labels": stats["chart_labels"],
        "chart_data": stats["chart_data"],
    })


@api_bp.route("/goals")
@login_required
def api_goals():
    goals = get_user_goals(current_user.id)
    return jsonify(goals.get("goals", []))


@api_bp.route("/checkin", methods=["GET", "POST"])
@login_required
def api_checkin():
    if request.method == "GET":
        today = get_today_checkin(current_user.id)
        return jsonify(today or {})
    data = request.get_json() or {}
    statuses = data.get("statuses", {})
    save_checkin(
        current_user.id,
        statuses,
        energy=data.get("energy"),
        mood=data.get("mood"),
        note=sanitize_text(data.get("note"), 500),
    )
    return jsonify({"ok": True})


@api_bp.route("/chat", methods=["POST"])
@login_required
def api_chat():
    data = request.get_json() or {}
    message = sanitize_text(data.get("message"), 1000)
    if not message:
        return jsonify({"error": "Message required"}), 400
    save_message(current_user.id, "user", message)
    context = get_user_context_for_ai(current_user.id)
    response, offline = generate_reply(current_user.id, message, context)
    save_message(current_user.id, "bot", response)
    return jsonify({"response": response, "offline_mode": offline})
