from datetime import datetime
from openai import OpenAI, RateLimitError, AuthenticationError
from flask import current_app
from models.db import chat_messages_collection
from utils.helpers import generate_fallback_reply

SUGGESTED_PROMPTS = [
    "How's my week going?",
    "Motivate me today",
    "Plan my day",
    "What should I focus on?",
]

MAX_CONTEXT_MESSAGES = 12


def _get_client():
    return OpenAI(api_key=current_app.config["OPENAI_API_KEY"])


def get_chat_history(user_id, limit=50):
    return list(
        chat_messages_collection.find({"user_id": user_id})
        .sort("created_at", 1)
        .limit(limit)
    )


def save_message(user_id, role, text):
    chat_messages_collection.insert_one({
        "user_id": user_id,
        "role": role,
        "text": text,
        "created_at": datetime.utcnow(),
    })


def _build_system_messages(context):
    goals_text = ""
    for g in context.get("goals", []):
        goals_text += f"- {g['action']}: {g.get('target', '')}\n"

    today_status = context.get("today_statuses", {})
    today_summary = ", ".join(f"{k}: {v}" for k, v in today_status.items()) or "not checked in yet"

    return [
        {
            "role": "system",
            "content": f"""You are Twin-Mate, a smart AI life coach.

User stats:
- Streak: {context['streak_days']} days
- Weekly completion: {context['weekly_completion']}%
- Overall completion: {context['overall_completion']}%
- Total days tracked: {context['total_days']}
- Days showed up: {context['show_up_days']}
- Last energy: {context.get('last_energy')}
- Last mood: {context.get('last_mood')}
- Today: {today_summary}

Goals:
{goals_text or 'No goals set yet.'}

Be supportive, honest, and actionable. Keep responses short and motivating.""",
        }
    ]


def _trim_history(messages):
    if len(messages) <= MAX_CONTEXT_MESSAGES:
        return messages
    return messages[-MAX_CONTEXT_MESSAGES:]


def generate_reply(user_id, user_message, context):
    history = get_chat_history(user_id)
    messages = _build_system_messages(context)

    # History already includes the just-saved user message — don't append it again.
    for m in history:
        role = "assistant" if m["role"] == "bot" else "user"
        messages.append({"role": role, "content": m["text"]})

    messages = _trim_history(messages)

    try:
        client = _get_client()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
        )
        return response.choices[0].message.content, False
    except (AuthenticationError, RateLimitError):
        pass
    except Exception:
        pass

    fallback = generate_fallback_reply(
        user_message,
        context["total_days"],
        context["show_up_days"],
        context.get("last_energy"),
        context.get("last_mood"),
    )
    return fallback, True


def migrate_chat_from_user_doc(user_id, user_doc):
    legacy = user_doc.get("chat_history", [])
    if not legacy:
        return
    existing = chat_messages_collection.count_documents({"user_id": user_id})
    if existing > 0:
        return
    for msg in legacy:
        save_message(user_id, msg.get("role", "user"), msg.get("text", ""))
