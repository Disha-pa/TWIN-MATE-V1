"""Wipe Twin Mate user accounts and related data for a fresh start."""
from app import create_app
from models.db import (
    users_collection,
    goals_collection,
    checkins_collection,
    chat_messages_collection,
    push_subscriptions_collection,
)

app = create_app("development")

with app.app_context():
    before = users_collection.count_documents({})
    print(f"Users before: {before}")

    u = users_collection.delete_many({})
    g = goals_collection.delete_many({})
    c = checkins_collection.delete_many({})
    m = chat_messages_collection.delete_many({})
    p = push_subscriptions_collection.delete_many({})

    print(f"Deleted users: {u.deleted_count}")
    print(f"Deleted goals: {g.deleted_count}")
    print(f"Deleted checkins: {c.deleted_count}")
    print(f"Deleted chat messages: {m.deleted_count}")
    print(f"Deleted push subscriptions: {p.deleted_count}")
    print(f"Users after: {users_collection.count_documents({})}")
    print("Done. Database is empty — you can sign up fresh.")
