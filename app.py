from flask import Flask, render_template, request, redirect, url_for, session
from models.db import users_collection, goals_collection, checkins_collection
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from openai import OpenAI
from openai import RateLimitError, AuthenticationError
import os
import re
import calendar
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = "your_secret_key"

# 🤖 OpenAI Client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


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
    return "You’re doing better than you think. Choose one task, start for 10 minutes, and keep the streak alive."


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
            f"Focus on making '{weakest_goal['action']}' easier so you can convert more days to ✅."
        )
    return (
        f"Reset week mode: streak {streak_days} days and completion {weekly_completion}%. "
        f"Prioritize one easy win daily on '{weakest_goal['action']}' to rebuild confidence quickly."
    )


# 🔐 Signup
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form.get("email")
        password = generate_password_hash(request.form.get("password"))

        if users_collection.find_one({"email": email}):
            return "User already exists"

        users_collection.insert_one({
            "email": email,
            "password": password,
            "chat_history": []
        })

        return redirect(url_for("login"))

    return render_template("signup.html")


# 🔐 Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = users_collection.find_one({"email": email})

        if user and check_password_hash(user["password"], password):
            session["user_id"] = str(user["_id"])
            session["user_email"] = user["email"]
            session["theme_key"] = f"theme_{session['user_id']}"
            return redirect(url_for("home"))

        return "Invalid credentials"

    return render_template("login.html")


# 🚪 Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# Splash
@app.route("/")
def splash():
    return redirect(url_for("login"))


# Home
@app.route("/home")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("home.html")


# ✅ Check-in
@app.route("/checkin", methods=["GET", "POST"])
def checkin():
    if "user_id" not in session:
        return redirect(url_for("login"))
    # Routine checkup is merged into dashboard.
    return redirect(url_for("dashboard"))


# 🎯 Goal Setup
@app.route("/goal", methods=["GET", "POST"])
def goal():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        data = {
            "user_id": session["user_id"],
            "category": request.form.get("category"),
            "goals": []
        }

        actions = request.form.getlist("action_name")
        targets = request.form.getlist("target_value")
        target_days_list = request.form.getlist("target_days")

        for a, t, td in zip(actions, targets, target_days_list):
            parsed_target_days = None
            if td and td.isdigit():
                parsed_target_days = int(td)
            else:
                digit_match = re.search(r"\d+", t or "")
                if digit_match:
                    parsed_target_days = int(digit_match.group(0))

            data["goals"].append({
                "action": a,
                "target": t,
                "target_days": parsed_target_days
            })

        goals_collection.update_one(
            {"user_id": session["user_id"]},
            {"$set": data},
            upsert=True
        )
        return redirect(url_for("checkin"))

    category = request.args.get("category")
    return render_template("goal_setup.html", category=category)


# 📊 Dashboard (ML + Prediction FIXED)
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["user_id"]
    goals = goals_collection.find_one({"user_id": user_id})
    if not goals:
        goals = {"user_id": user_id, "goals": [], "goal_statuses": {}}

    if request.method == "POST":
        form_type = request.form.get("form_type", "statuses")
        if form_type == "reminder":
            reminder_time = request.form.get("reminder_time", "")
            goals_collection.update_one(
                {"user_id": user_id},
                {"$set": {"reminder_time": reminder_time}},
                upsert=True
            )
            return redirect(url_for("dashboard"))

        statuses = {}
        for g in goals.get("goals", []):
            action_name = g.get("action")
            target_days = g.get("target_days") or 0
            action_status_list = []
            for day in range(1, target_days + 1):
                form_key = f"status__{action_name}__{day}"
                value = request.form.get(form_key, "")
                if value not in ["done", "not_done"]:
                    value = ""
                action_status_list.append(value)
            statuses[action_name] = action_status_list

        goals_collection.update_one(
            {"user_id": user_id},
            {"$set": {"goal_statuses": statuses}},
            upsert=True
        )
        return redirect(url_for("dashboard"))

    goal_statuses = goals.get("goal_statuses", {})
    reminder_time = goals.get("reminder_time", "20:00")
    goal_progress = []
    motivation_quotes = [
        "Small steps every day build unstoppable momentum.",
        "Progress beats perfection. Keep showing up.",
        "One consistent habit can change everything.",
        "You are closer than you think. Keep going.",
        "Discipline today becomes confidence tomorrow."
    ]

    if goals and goals.get("goals"):
        for g in goals.get("goals", []):
            action_name = g.get("action")
            target_text = g.get("target")
            target_days = g.get("target_days") or 0
            action_statuses = goal_statuses.get(action_name, [])
            completed_days = sum(1 for s in action_statuses if s == "done")
            missed_days = sum(1 for s in action_statuses if s == "not_done")
            marked_days = completed_days + missed_days

            is_complete = bool(target_days) and completed_days >= target_days
            progress_percent = 0
            if target_days and target_days > 0:
                progress_percent = min(100, int((completed_days / target_days) * 100))
            quote = motivation_quotes[completed_days % len(motivation_quotes)]

            goal_progress.append({
                "action": action_name,
                "target_text": target_text,
                "target_days": target_days,
                "completed_days": completed_days,
                "missed_days": missed_days,
                "marked_days": marked_days,
                "is_complete": is_complete,
                "progress_percent": progress_percent,
                "quote": quote
            })

    max_target_days = 0
    for gp in goal_progress:
        if gp["target_days"] and gp["target_days"] > max_target_days:
            max_target_days = gp["target_days"]

    day_headers = list(range(1, max_target_days + 1))
    goal_table_rows = []
    day_scores = []
    day_done_counts = []
    day_missed_counts = []
    day_total_counts = []

    for gp in goal_progress:
        action_statuses = goal_statuses.get(gp["action"], [])
        checks = []
        for day in day_headers:
            if not gp["target_days"] or day > gp["target_days"]:
                checks.append(None)
            else:
                if day - 1 < len(action_statuses):
                    checks.append(action_statuses[day - 1])
                else:
                    checks.append("")
        goal_table_rows.append({
            "action": gp["action"],
            "target_days": gp["target_days"],
            "checks": checks
        })

    for day in day_headers:
        applicable = 0
        done = 0
        for row in goal_table_rows:
            chk = row["checks"][day - 1]
            if chk is None:
                continue
            applicable += 1
            if chk == "done":
                done += 1
        if applicable == 0:
            day_scores.append(0)
        else:
            day_scores.append(int((done / applicable) * 100))
        day_done_counts.append(done)
        day_missed_counts.append(
            sum(1 for row in goal_table_rows if row["checks"][day - 1] == "not_done")
        )
        day_total_counts.append(applicable)

    weekly_slice = day_scores[-7:] if day_scores else []
    weekly_completion = int(sum(weekly_slice) / len(weekly_slice)) if weekly_slice else 0

    streak_days = 0
    for score in reversed(day_scores):
        if score >= 60:
            streak_days += 1
        else:
            break

    # Heatmap: show last 35 day-cells
    heatmap_days = []
    recent_window = day_scores[-35:] if day_scores else []
    start_date = datetime.now().date() - timedelta(days=max(0, len(recent_window) - 1))
    for i, score in enumerate(recent_window):
        day_label = (start_date + timedelta(days=i)).strftime("%d %b")
        heatmap_days.append({
            "label": day_label,
            "score": score
        })

    # Reminder banner when it's reminder time and latest day is not yet mostly done
    reminder_banner = ""
    if reminder_time and day_scores:
        now = datetime.now().strftime("%H:%M")
        latest_score = day_scores[-1]
        if now >= reminder_time and latest_score < 60:
            reminder_banner = "Reminder: your daily tracker still has pending items. Mark today's progress."

    weekly_review = build_weekly_review(streak_days, weekly_completion, goal_progress)

    total_done = sum(day_done_counts)
    total_missed = sum(day_missed_counts)
    total_marked = total_done + total_missed
    overall_completion = int((total_done / total_marked) * 100) if total_marked else 0

    badges = []
    if streak_days >= 3:
        badges.append("🔥 3-Day Streak")
    if streak_days >= 7:
        badges.append("🚀 7-Day Streak")
    if overall_completion >= 70 and total_marked >= 10:
        badges.append("✅ Consistency Pro")
    if total_done >= 25:
        badges.append("🏆 25 Tasks Done")

    level = max(1, total_done // 10 + 1)

    # Phase 2/3: interactive month calendar with day details
    today = datetime.now().date()
    timeline_by_date = {}
    for idx, score in enumerate(day_scores):
        day_date = today - timedelta(days=(len(day_scores) - 1 - idx))
        per_goal = []
        for row in goal_table_rows:
            status_value = row["checks"][idx] if idx < len(row["checks"]) else None
            if status_value is None:
                continue
            per_goal.append({
                "action": row["action"],
                "status": status_value
            })
        timeline_by_date[day_date.isoformat()] = {
            "score": score,
            "done": day_done_counts[idx],
            "missed": day_missed_counts[idx],
            "total": day_total_counts[idx],
            "per_goal": per_goal
        }

    selected_year = request.args.get("year", type=int) or today.year
    selected_month = request.args.get("month", type=int) or today.month
    if selected_month < 1 or selected_month > 12:
        selected_month = today.month

    month_first = datetime(selected_year, selected_month, 1).date()
    _, days_in_month = calendar.monthrange(selected_year, selected_month)
    leading_blanks = month_first.weekday()  # Monday=0
    month_cells = []
    for _ in range(leading_blanks):
        month_cells.append(None)

    for day_num in range(1, days_in_month + 1):
        date_obj = datetime(selected_year, selected_month, day_num).date()
        key = date_obj.isoformat()
        day_data = timeline_by_date.get(
            key, {"score": 0, "done": 0, "missed": 0, "total": 0, "per_goal": []}
        )
        month_cells.append({
            "day": day_num,
            "date_key": key,
            "score": day_data["score"],
            "done": day_data["done"],
            "missed": day_data["missed"],
            "total": day_data["total"],
            "per_goal": day_data["per_goal"]
        })

    while len(month_cells) % 7 != 0:
        month_cells.append(None)

    calendar_weeks = [
        month_cells[i:i + 7] for i in range(0, len(month_cells), 7)
    ]

    selected_date = request.args.get("selected_date", today.isoformat())
    try:
        selected_date_obj = datetime.fromisoformat(selected_date).date()
    except ValueError:
        selected_date_obj = today
        selected_date = today.isoformat()
    selected_day_details = timeline_by_date.get(
        selected_date, {"score": 0, "done": 0, "missed": 0, "total": 0, "per_goal": []}
    )
    prev_week_date = (selected_date_obj - timedelta(days=7)).isoformat()
    next_week_date = (selected_date_obj + timedelta(days=7)).isoformat()

    # Weekday insights
    weekday_scores = {i: [] for i in range(7)}
    for date_key, details in timeline_by_date.items():
        d = datetime.fromisoformat(date_key).date()
        weekday_scores[d.weekday()].append(details["score"])

    weekday_avg = {}
    for idx, values in weekday_scores.items():
        weekday_avg[idx] = int(sum(values) / len(values)) if values else 0

    weekday_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    best_idx = max(weekday_avg, key=lambda k: weekday_avg[k]) if weekday_avg else 0
    worst_idx = min(weekday_avg, key=lambda k: weekday_avg[k]) if weekday_avg else 0
    best_weekday = f"{weekday_names[best_idx]} ({weekday_avg[best_idx]}%)"
    worst_weekday = f"{weekday_names[worst_idx]} ({weekday_avg[worst_idx]}%)"

    # Month navigation
    prev_month_year = selected_year
    prev_month = selected_month - 1
    if prev_month == 0:
        prev_month = 12
        prev_month_year -= 1

    next_month_year = selected_year
    next_month = selected_month + 1
    if next_month == 13:
        next_month = 1
        next_month_year += 1

    return render_template(
        "dashboard.html",
        goals=goals,
        goal_progress=goal_progress,
        day_headers=day_headers,
        goal_table_rows=goal_table_rows,
        streak_days=streak_days,
        weekly_completion=weekly_completion,
        heatmap_days=heatmap_days,
        reminder_time=reminder_time,
        reminder_banner=reminder_banner,
        weekly_review=weekly_review,
        total_done=total_done,
        total_missed=total_missed,
        overall_completion=overall_completion,
        badges=badges,
        level=level,
        calendar_weeks=calendar_weeks,
        selected_date=selected_date,
        selected_day_details=selected_day_details,
        month_name=month_first.strftime("%B %Y"),
        selected_year=selected_year,
        selected_month=selected_month,
        prev_month_year=prev_month_year,
        prev_month=prev_month,
        next_month_year=next_month_year,
        next_month=next_month,
        prev_week_date=prev_week_date,
        next_week_date=next_week_date,
        best_weekday=best_weekday,
        worst_weekday=worst_weekday
    )


# 🤖 AI Chat
@app.route("/chat", methods=["GET", "POST"])
def chat():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if "chat_offline_mode" not in session:
        session["chat_offline_mode"] = False

    user_doc = None
    user_email = session.get("user_email")
    if user_email:
        user_doc = users_collection.find_one({"email": user_email})
    else:
        try:
            user_doc = users_collection.find_one({"_id": ObjectId(session["user_id"])})
        except Exception:
            user_doc = None

    chat_history = user_doc.get("chat_history", []) if user_doc else []
    user_message = ""

    if request.method == "POST":
        user_message = request.form.get("message")
        if user_message:
            chat_history.append({"role": "user", "text": user_message})
    else:
        return render_template(
            "chat.html",
            chat_history=chat_history,
            chat_offline_mode=session.get("chat_offline_mode", False)
        )

    if not user_message:
        return render_template(
            "chat.html",
            chat_history=chat_history,
            chat_offline_mode=session.get("chat_offline_mode", False)
        )

    # 🧠 Build user context
    checkin = list(checkins_collection.find({"user_id": session["user_id"]}))
    goal = goals_collection.find_one({"user_id": session["user_id"]})

    total_days = len(checkin)
    show_up_days = 0

    last_energy = None
    last_emotion = None

    for d in checkin:
        log = d.get("log", [])
        if any(item["status"] in ["complete", "partial", "tried"] for item in log):
             show_up_days += 1

    if checkin:
        last_energy = checkin[-1].get("energy")
        last_emotion = checkin[-1].get("emotion")

    # 🤖 Smart system prompt
    messages = [
        {
            "role": "system",
            "content": f"""
    You are Twin-Mate, a smart AI life coach.

    User stats:
    - Total days tracked: {total_days}
    - Days showed up: {show_up_days}
    - Last energy: {last_energy}
    - Last emotion: {last_emotion}

    Your behavior:
    - Be supportive but honest
    - Give actionable advice
    - Act like a personal coach + friend
    - Keep responses short, human, and motivating
    """
        }
    ]

    if goal:
        goal_text = "User goals:\n"
        for g in goal.get("goals", []):
            goal_text += f"- {g['action']}: {g['target']}\n"

        messages.append({"role": "system", "content": goal_text})

    for m in chat_history:
        role = "assistant" if m["role"] == "bot" else "user"
        messages.append({"role": role, "content": m["text"]})

    try:
        ai_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages
        )
        response = ai_response.choices[0].message.content
        session["chat_offline_mode"] = False
    except AuthenticationError:
        fallback = generate_fallback_reply(
            user_message, total_days, show_up_days, last_energy, last_emotion
        )
        response = fallback
        session["chat_offline_mode"] = True
    except RateLimitError:
        fallback = generate_fallback_reply(
            user_message, total_days, show_up_days, last_energy, last_emotion
        )
        response = fallback
        session["chat_offline_mode"] = True
    except Exception:
        fallback = generate_fallback_reply(
            user_message, total_days, show_up_days, last_energy, last_emotion
        )
        response = fallback
        session["chat_offline_mode"] = True

    chat_history.append({"role": "bot", "text": response})
    if user_doc:
        users_collection.update_one(
            {"_id": user_doc["_id"]},
            {"$set": {"chat_history": chat_history}}
        )

    return render_template(
        "chat.html",
        chat_history=chat_history,
        chat_offline_mode=session.get("chat_offline_mode", False)
    )


if __name__ == "__main__":
    app.run(debug=True)
