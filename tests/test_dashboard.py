from models.db import goals_collection, users_collection


def _login(client):
    client.post("/signup", data={"email": "dash@example.com", "password": "secret12"}, follow_redirects=True)


def test_dashboard_with_goals(client):
    _login(client)
    user = users_collection.find_one({"email": "dash@example.com"})
    goals_collection.insert_one({
        "user_id": str(user["_id"]),
        "category": "Daily",
        "goals": [{"action": "Water", "target": "8 glasses", "target_days": 7}],
    })
    rv = client.get("/home")
    assert rv.status_code == 200
    assert b"Focus Area" in rv.data
    rv = client.get("/dashboard")
    assert rv.status_code == 200
    assert b"Tracker" in rv.data


def test_api_dashboard(client):
    _login(client)
    rv = client.get("/api/v1/dashboard")
    assert rv.status_code == 200
    data = rv.get_json()
    assert "streak_days" in data
    assert "weekly_completion" in data


def test_profile_update_username_and_age(client):
    _login(client)
    rv = client.post("/profile", data={
        "action": "update",
        "name": "Disha",
        "username": "disha_01",
        "age": "21",
        "timezone": "UTC",
    }, follow_redirects=True)
    assert rv.status_code == 200
    assert b"Profile updated" in rv.data or b"@disha_01" in rv.data
    user = users_collection.find_one({"email": "dash@example.com"})
    assert user.get("username") == "disha_01"
    assert user.get("age") == 21
    assert user.get("name") == "Disha"
