import json
import requests
from datetime import datetime
from flask import current_app
from models.db import users_collection, checkins_collection, push_subscriptions_collection
from utils.helpers import today_iso

try:
    from pywebpush import webpush, WebPushException
except ImportError:
    webpush = None
    WebPushException = Exception


def send_email(to_email, subject, html_body):
    resend_key = current_app.config.get("RESEND_API_KEY")
    sendgrid_key = current_app.config.get("SENDGRID_API_KEY")
    mail_from = current_app.config.get("MAIL_FROM", "noreply@twinmate.app")

    if resend_key:
        try:
            resp = requests.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {resend_key}", "Content-Type": "application/json"},
                json={"from": mail_from, "to": [to_email], "subject": subject, "html": html_body},
                timeout=10,
            )
            return resp.status_code in (200, 201)
        except Exception:
            return False

    if sendgrid_key:
        try:
            resp = requests.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={"Authorization": f"Bearer {sendgrid_key}", "Content-Type": "application/json"},
                json={
                    "personalizations": [{"to": [{"email": to_email}]}],
                    "from": {"email": mail_from},
                    "subject": subject,
                    "content": [{"type": "text/html", "value": html_body}],
                },
                timeout=10,
            )
            return resp.status_code in (200, 202)
        except Exception:
            return False
    return False


def send_web_push(subscription, payload):
    if not webpush:
        return False
    try:
        webpush(
            subscription_info=subscription,
            data=json.dumps(payload),
            vapid_private_key=current_app.config.get("VAPID_PRIVATE_KEY"),
            vapid_claims={"sub": current_app.config.get("VAPID_CLAIMS_EMAIL")},
        )
        return True
    except WebPushException:
        return False


def send_reminder_to_user(user):
    user_id = str(user["_id"])
    today = today_iso()
    checked_in = checkins_collection.find_one({"user_id": user_id, "date": today})
    if checked_in and checked_in.get("statuses"):
        return False

    email = user.get("email")
    name = user.get("name") or email.split("@")[0]
    subject = "Twin-Mate: Daily check-in reminder"
    body = f"<p>Hi {name},</p><p>You haven't checked in today. Open Twin-Mate and log your progress.</p>"

    if email:
        send_email(email, subject, body)

    subs = push_subscriptions_collection.find({"user_id": user_id})
    for sub in subs:
        send_web_push(sub.get("subscription", {}), {
            "title": "Twin-Mate Reminder",
            "body": "Time for your daily check-in!",
        })
    return True


def run_daily_reminders():
    now = datetime.now().strftime("%H:%M")
    today = today_iso()
    users = users_collection.find({
        "reminder_time": {"$lte": now},
        "$or": [
            {"last_reminded_date": {"$exists": False}},
            {"last_reminded_date": {"$ne": today}},
        ],
    })
    sent = 0
    for user in users:
        if send_reminder_to_user(user):
            users_collection.update_one(
                {"_id": user["_id"]},
                {"$set": {"last_reminded_date": today}},
            )
            sent += 1
    return sent
