from flask import render_template, request
from utils.auth import login_required, current_user

from blueprints.chat import chat_bp
from models.db import users_collection
from services.ai_service import (
    SUGGESTED_PROMPTS,
    generate_reply,
    get_chat_history,
    save_message,
    migrate_chat_from_user_doc,
)
from services.stats_service import get_user_context_for_ai


@chat_bp.route("/chat", methods=["GET", "POST"])
@login_required
def chat():
    user_doc = users_collection.find_one({"_id": current_user.doc["_id"]})
    migrate_chat_from_user_doc(current_user.id, user_doc or {})

    chat_history = get_chat_history(current_user.id)
    offline_mode = False

    if request.method == "POST":
        user_message = request.form.get("message", "").strip()
        if user_message:
            save_message(current_user.id, "user", user_message)
            context = get_user_context_for_ai(current_user.id)
            response, offline_mode = generate_reply(current_user.id, user_message, context)
            save_message(current_user.id, "bot", response)
            chat_history = get_chat_history(current_user.id)

    return render_template(
        "chat.html",
        chat_history=chat_history,
        chat_offline_mode=offline_mode,
        suggested_prompts=SUGGESTED_PROMPTS,
    )
