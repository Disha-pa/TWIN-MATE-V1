from datetime import datetime, timedelta
import calendar
from models.db import checkins_collection, goals_collection
from utils.helpers import build_weekly_review, week_start


def migrate_legacy_statuses(user_id, goals_doc):
    """Convert old goal_statuses arrays to date-keyed checkins."""
    if not goals_doc:
        return
    legacy = goals_doc.get("goal_statuses")
    if not legacy:
        return
    if goals_doc.get("legacy_migrated"):
        return

    start_date = datetime.now().date() - timedelta(days=364)
    for action_name, statuses in legacy.items():
        for idx, status in enumerate(statuses):
            if status not in ("done", "not_done"):
                continue
            day_date = (start_date + timedelta(days=idx)).isoformat()
            existing = checkins_collection.find_one({"user_id": user_id, "date": day_date})
            if existing:
                statuses_map = existing.get("statuses", {})
                statuses_map[action_name] = status
                checkins_collection.update_one(
                    {"_id": existing["_id"]},
                    {"$set": {"statuses": statuses_map}},
                )
            else:
                checkins_collection.insert_one({
                    "user_id": user_id,
                    "date": day_date,
                    "statuses": {action_name: status},
                    "energy": None,
                    "mood": None,
                    "note": "",
                    "created_at": datetime.utcnow(),
                })

    goals_collection.update_one(
        {"user_id": user_id},
        {"$unset": {"goal_statuses": ""}, "$set": {"legacy_migrated": True}},
    )


def get_user_goals(user_id):
    goals = goals_collection.find_one({"user_id": user_id})
    if not goals:
        return {"user_id": user_id, "goals": []}
    migrate_legacy_statuses(user_id, goals)
    return goals_collection.find_one({"user_id": user_id}) or {"user_id": user_id, "goals": []}


def get_checkins_for_user(user_id, days=365):
    cutoff = (datetime.now().date() - timedelta(days=days - 1)).isoformat()
    return list(
        checkins_collection.find(
            {"user_id": user_id, "date": {"$gte": cutoff}},
        ).sort("date", 1)
    )


def get_today_checkin(user_id):
    today = datetime.now().date().isoformat()
    return checkins_collection.find_one({"user_id": user_id, "date": today})


def save_checkin(user_id, statuses, energy=None, mood=None, note=""):
    today = datetime.now().date().isoformat()
    doc = {
        "user_id": user_id,
        "date": today,
        "statuses": statuses,
        "energy": energy,
        "mood": mood,
        "note": note,
        "updated_at": datetime.utcnow(),
    }
    checkins_collection.update_one(
        {"user_id": user_id, "date": today},
        {"$set": doc, "$setOnInsert": {"created_at": datetime.utcnow()}},
        upsert=True,
    )
    return doc


def _day_score(statuses_map, goal_actions):
    applicable = [a for a in goal_actions if a in statuses_map and statuses_map[a]]
    if not applicable:
        return 0, 0, 0, 0
    done = sum(1 for a in applicable if statuses_map[a] == "done")
    missed = sum(1 for a in applicable if statuses_map[a] == "not_done")
    score = int((done / len(applicable)) * 100)
    return score, done, missed, len(applicable)


def build_dashboard_stats(user_id, selected_year=None, selected_month=None, selected_date=None):
    goals = get_user_goals(user_id)
    goal_list = goals.get("goals", [])
    goal_actions = [g["action"] for g in goal_list]
    checkins = get_checkins_for_user(user_id)
    checkin_by_date = {c["date"]: c for c in checkins}

    today = datetime.now().date()
    selected_date = selected_date or today.isoformat()
    try:
        selected_date_obj = datetime.fromisoformat(selected_date).date()
    except ValueError:
        selected_date_obj = today
        selected_date = today.isoformat()

    timeline_by_date = {}
    for c in checkins:
        statuses = c.get("statuses", {})
        score, done, missed, total = _day_score(statuses, goal_actions)
        per_goal = [
            {"action": a, "status": statuses.get(a, "")}
            for a in goal_actions
            if statuses.get(a)
        ]
        timeline_by_date[c["date"]] = {
            "score": score,
            "done": done,
            "missed": missed,
            "total": total,
            "per_goal": per_goal,
            "energy": c.get("energy"),
            "mood": c.get("mood"),
            "note": c.get("note", ""),
        }

    motivation_quotes = [
        "Small steps every day build unstoppable momentum.",
        "Progress beats perfection. Keep showing up.",
        "One consistent habit can change everything.",
        "You are closer than you think. Keep going.",
        "Discipline today becomes confidence tomorrow.",
    ]

    goal_progress = []
    for g in goal_list:
        action = g["action"]
        target_days = g.get("target_days") or 0
        completed_days = 0
        missed_days = 0
        for c in checkins:
            st = c.get("statuses", {}).get(action)
            if st == "done":
                completed_days += 1
            elif st == "not_done":
                missed_days += 1
        marked_days = completed_days + missed_days
        progress_percent = min(100, int((completed_days / target_days) * 100)) if target_days else 0
        goal_progress.append({
            "action": action,
            "target_text": g.get("target", ""),
            "target_days": target_days,
            "completed_days": completed_days,
            "missed_days": missed_days,
            "marked_days": marked_days,
            "is_complete": bool(target_days) and completed_days >= target_days,
            "progress_percent": progress_percent,
            "quote": motivation_quotes[completed_days % len(motivation_quotes)],
        })

    # Week view (Mon-Sun current week)
    ws = week_start()
    week_days = []
    for i in range(7):
        d = ws + timedelta(days=i)
        key = d.isoformat()
        data = timeline_by_date.get(key, {"score": 0, "done": 0, "missed": 0, "total": 0, "per_goal": []})
        week_days.append({
            "date": key,
            "label": d.strftime("%a"),
            "day_num": d.day,
            "is_today": key == today.isoformat(),
            **data,
        })

    # Daily scores for streak/heatmap (last 35 days)
    day_scores = []
    for i in range(35):
        d = today - timedelta(days=34 - i)
        key = d.isoformat()
        day_scores.append(timeline_by_date.get(key, {"score": 0})["score"])

    weekly_slice = day_scores[-7:] if day_scores else []
    weekly_completion = int(sum(weekly_slice) / len(weekly_slice)) if weekly_slice else 0

    streak_days = 0
    for i in range(len(day_scores) - 1, -1, -1):
        d = today - timedelta(days=(len(day_scores) - 1 - i))
        key = d.isoformat()
        if key not in timeline_by_date:
            break
        if day_scores[i] >= 60:
            streak_days += 1
        else:
            break

    heatmap_days = []
    start_date = today - timedelta(days=34)
    for i, score in enumerate(day_scores):
        day_label = (start_date + timedelta(days=i)).strftime("%d %b")
        heatmap_days.append({"label": day_label, "score": score})

    total_done = sum(t["done"] for t in timeline_by_date.values())
    total_missed = sum(t["missed"] for t in timeline_by_date.values())
    total_marked = total_done + total_missed
    overall_completion = int((total_done / total_marked) * 100) if total_marked else 0

    badges = []
    if streak_days >= 3:
        badges.append("3-Day Streak")
    if streak_days >= 7:
        badges.append("7-Day Streak")
    if overall_completion >= 70 and total_marked >= 10:
        badges.append("Consistency Pro")
    if total_done >= 25:
        badges.append("25 Tasks Done")

    level = max(1, total_done // 10 + 1)
    weekly_review = build_weekly_review(streak_days, weekly_completion, goal_progress)

    # Weekday insights
    weekday_scores = {i: [] for i in range(7)}
    for date_key, details in timeline_by_date.items():
        d = datetime.fromisoformat(date_key).date()
        weekday_scores[d.weekday()].append(details["score"])
    weekday_avg = {i: int(sum(v) / len(v)) if v else 0 for i, v in weekday_scores.items()}
    weekday_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    best_idx = max(weekday_avg, key=lambda k: weekday_avg[k]) if weekday_avg else 0
    worst_idx = min(weekday_avg, key=lambda k: weekday_avg[k]) if weekday_avg else 0

    # Calendar
    selected_year = selected_year or today.year
    selected_month = selected_month or today.month
    month_first = datetime(selected_year, selected_month, 1).date()
    _, days_in_month = calendar.monthrange(selected_year, selected_month)
    leading_blanks = month_first.weekday()
    month_cells = [None] * leading_blanks
    for day_num in range(1, days_in_month + 1):
        date_obj = datetime(selected_year, selected_month, day_num).date()
        key = date_obj.isoformat()
        day_data = timeline_by_date.get(
            key, {"score": 0, "done": 0, "missed": 0, "total": 0, "per_goal": []}
        )
        month_cells.append({
            "day": day_num,
            "date_key": key,
            **day_data,
        })
    while len(month_cells) % 7 != 0:
        month_cells.append(None)
    calendar_weeks = [month_cells[i:i + 7] for i in range(0, len(month_cells), 7)]

    prev_month_year, prev_month = selected_year, selected_month - 1
    if prev_month == 0:
        prev_month, prev_month_year = 12, selected_year - 1
    next_month_year, next_month = selected_year, selected_month + 1
    if next_month == 13:
        next_month, next_month_year = 1, selected_year + 1

    selected_day_details = timeline_by_date.get(
        selected_date, {"score": 0, "done": 0, "missed": 0, "total": 0, "per_goal": []}
    )

    chart_labels = [(today - timedelta(days=6 - i)).strftime("%a") for i in range(7)]
    chart_data = day_scores[-7:] if day_scores else [0] * 7

    today_checkin = get_today_checkin(user_id)
    focus_tip = _build_focus_tip(goal_progress, today_checkin, streak_days, weekly_completion)

    return {
        "goals": goals,
        "goal_progress": goal_progress,
        "week_days": week_days,
        "streak_days": streak_days,
        "weekly_completion": weekly_completion,
        "heatmap_days": heatmap_days,
        "weekly_review": weekly_review,
        "total_done": total_done,
        "total_missed": total_missed,
        "overall_completion": overall_completion,
        "badges": badges,
        "level": level,
        "calendar_weeks": calendar_weeks,
        "selected_date": selected_date,
        "selected_day_details": selected_day_details,
        "month_name": month_first.strftime("%B %Y"),
        "selected_year": selected_year,
        "selected_month": selected_month,
        "prev_month_year": prev_month_year,
        "prev_month": prev_month,
        "next_month_year": next_month_year,
        "next_month": next_month,
        "prev_week_date": (selected_date_obj - timedelta(days=7)).isoformat(),
        "next_week_date": (selected_date_obj + timedelta(days=7)).isoformat(),
        "best_weekday": f"{weekday_names[best_idx]} ({weekday_avg[best_idx]}%)",
        "worst_weekday": f"{weekday_names[worst_idx]} ({weekday_avg[worst_idx]}%)",
        "chart_labels": chart_labels,
        "chart_data": chart_data,
        "focus_tip": focus_tip,
        "today_checkin": today_checkin,
    }


def _build_focus_tip(goal_progress, today_checkin, streak_days, weekly_completion):
    if not goal_progress:
        return "Set your first goals to get a personalized focus tip for today."
    weakest = min(goal_progress, key=lambda g: g.get("progress_percent", 0))
    if today_checkin and today_checkin.get("statuses"):
        pending = [
            g["action"] for g in goal_progress
            if today_checkin.get("statuses", {}).get(g["action"]) not in ("done", "not_done")
        ]
        if pending:
            return f"Finish today's check-in: start with '{pending[0]}' — small wins keep your {streak_days}-day streak alive."
    if weekly_completion < 50:
        return f"Recovery mode: make '{weakest['action']}' easier today — aim for the smallest possible version."
    return f"Strong momentum at {weekly_completion}% this week. Push '{weakest['action']}' to balance your habits."


def get_user_context_for_ai(user_id):
    stats = build_dashboard_stats(user_id)
    checkins = get_checkins_for_user(user_id, days=90)
    today = get_today_checkin(user_id)
    last = checkins[-1] if checkins else None
    return {
        "streak_days": stats["streak_days"],
        "weekly_completion": stats["weekly_completion"],
        "overall_completion": stats["overall_completion"],
        "total_days": len(checkins),
        "show_up_days": sum(1 for c in checkins if c.get("statuses")),
        "last_energy": last.get("energy") if last else None,
        "last_mood": last.get("mood") if last else None,
        "today_statuses": today.get("statuses", {}) if today else {},
        "goal_progress": stats["goal_progress"],
        "goals": stats["goals"].get("goals", []),
    }
