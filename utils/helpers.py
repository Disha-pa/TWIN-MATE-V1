import re
from datetime import datetime, timedelta


def generate_fallback_reply(user_message, total_days, show_up_days, last_energy, last_emotion):
    text = (user_message or "").lower()
    words = set(re.findall(r"[a-z]+", text))

    if "happy" in words or "good" in words or "great" in words:
        return "Love that energy. Use it now: finish one important goal today and lock in the win."
    if "sad" in words or "stressed" in words or "anxious" in words:
        return "You're not alone. Take one tiny step now, then pause and breathe for 60 seconds. Small wins still count."
    if "tired" in words or ("low" in words and "energy" in words):
        return "Low-energy day plan: pick the easiest task and do it for just 5 minutes. Done is better than perfect."
    if "skip" in words or "cant" in words or "fail" in words:
        return "Reset moment: do one micro-task right now and call today a comeback, not a failure."
    if "plan" in words or "routine" in words:
        return "Try this simple routine: 1) one priority task, 2) one health task, 3) one reset break."

    if total_days == 0:
        return "Let's start your streak today. Pick one goal and complete the smallest possible version of it."
    if show_up_days >= max(1, int(total_days * 0.7)):
        return "You're building consistency really well. Push one meaningful task today to keep momentum."
    if last_energy == "Low":
        return "Since your last energy was low, choose a lighter task first. Start easy, then build momentum."
    if last_emotion:
        return f"Noted your last mood as {last_emotion}. Keep it simple today: one clear action and one small win."
    return "You're doing better than you think. Choose one task, start for 10 minutes, and keep the streak alive."


def build_weekly_review(streak_days, weekly_completion, goal_progress):
    if not goal_progress:
        return "Set your first goals to get a personalized weekly review."

    top_goal = max(goal_progress, key=lambda g: g.get("progress_percent", 0))
    weakest_goal = min(goal_progress, key=lambda g: g.get("progress_percent", 0))

    tone = "strong"
    if weekly_completion < 40:
        tone = "recovery"
    elif weekly_completion < 70:
        tone = "steady"

    if tone == "strong":
        return (
            f"Great week. Your consistency streak is {streak_days} days and weekly completion is "
            f"{weekly_completion}%. Keep momentum by pushing '{top_goal['action']}' and improving "
            f"'{weakest_goal['action']}' with one small daily action."
        )
    if tone == "steady":
        return (
            f"Solid progress. Streak is {streak_days} days with {weekly_completion}% weekly completion. "
            f"Focus on making '{weakest_goal['action']}' easier so you can convert more days to done."
        )
    return (
        f"Reset week mode: streak {streak_days} days and completion {weekly_completion}%. "
        f"Prioritize one easy win daily on '{weakest_goal['action']}' to rebuild confidence quickly."
    )


def today_iso():
    return datetime.now().date().isoformat()


def week_start(date_obj=None):
    d = date_obj or datetime.now().date()
    return d - timedelta(days=d.weekday())


def sanitize_text(value, max_len=500):
    if not value:
        return ""
    return str(value).strip()[:max_len]


AVATAR_COLORS = ["#ffb6d9", "#b5d8ff", "#c8f7c5", "#ffe4a3", "#d4b5ff", "#ffd6a5"]
