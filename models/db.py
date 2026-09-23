from pymongo import MongoClient, ASCENDING, DESCENDING

_client = None
_db = None

users_collection = None
goals_collection = None
checkins_collection = None
chat_messages_collection = None
push_subscriptions_collection = None


def init_db(app):
    global _client, _db
    global users_collection, goals_collection, checkins_collection
    global chat_messages_collection, push_subscriptions_collection

    _client = MongoClient(app.config["MONGO_URI"])
    _db = _client[app.config["DB_NAME"]]

    users_collection = _db["users"]
    goals_collection = _db["goals"]
    checkins_collection = _db["checkins"]
    chat_messages_collection = _db["chat_messages"]
    push_subscriptions_collection = _db["push_subscriptions"]

    users_collection.create_index("email", unique=True)
    try:
        users_collection.create_index(
            "username",
            unique=True,
            partialFilterExpression={"username": {"$gt": ""}},
        )
    except Exception:
        try:
            users_collection.drop_index("username_1")
        except Exception:
            pass
        try:
            users_collection.create_index(
                "username",
                unique=True,
                partialFilterExpression={"username": {"$gt": ""}},
            )
        except Exception:
            pass
    users_collection.update_many({"username": ""}, {"$unset": {"username": ""}})
    try:
        goals_collection.create_index("user_id", unique=True)
    except Exception:
        pass
    try:
        checkins_collection.create_index([("user_id", ASCENDING), ("date", DESCENDING)])
        checkins_collection.create_index(
            [("user_id", ASCENDING), ("date", ASCENDING)], unique=True
        )
    except Exception:
        pass
    try:
        chat_messages_collection.create_index(
            [("user_id", ASCENDING), ("created_at", DESCENDING)]
        )
    except Exception:
        pass
    try:
        push_subscriptions_collection.create_index("user_id")
    except Exception:
        pass


# get_db kept for scripts/extensions that need raw DB access
def get_db():
    return _db
