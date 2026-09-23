import os

os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault("TEST_DB_NAME", "TWIN_MATE_V1_TEST")
os.environ.setdefault("SECRET_KEY", "test-secret-key")

import pytest
import models.db as database
from app import create_app
from models.db import init_db


@pytest.fixture
def app():
    application = create_app("testing")
    application.config["TESTING"] = True
    application.config["WTF_CSRF_ENABLED"] = False
    init_db(application)
    yield application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def clean_db(app):
    if database.users_collection is not None:
        database.users_collection.delete_many({})
        database.goals_collection.delete_many({})
        database.checkins_collection.delete_many({})
        database.chat_messages_collection.delete_many({})
        database.push_subscriptions_collection.delete_many({})
    yield
