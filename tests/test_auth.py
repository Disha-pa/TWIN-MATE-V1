def test_signup_and_login(client):
    rv = client.post("/signup", data={
        "email": "test@example.com",
        "password": "secret12",
    }, follow_redirects=True)
    assert rv.status_code == 200
    assert b"Choose Your Focus Area" in rv.data

    # Other pages must stay logged in (no bounce back to login)
    rv = client.get("/checkin", follow_redirects=False)
    # No goals yet → app sends you to Home (still authenticated, not Login)
    assert rv.status_code in (200, 302)
    if rv.status_code == 302:
        assert "/login" not in (rv.headers.get("Location") or "")
        assert "/home" in (rv.headers.get("Location") or "")
    else:
        assert b"Enter your email" not in rv.data

    rv = client.get("/profile", follow_redirects=False)
    assert rv.status_code == 200
    assert b"Profile" in rv.data
    assert b"Enter your email" not in rv.data

    rv = client.get("/dashboard", follow_redirects=False)
    assert rv.status_code == 200
    assert b"Welcome Back" not in rv.data
    assert b"Enter your email" not in rv.data

    rv = client.get("/chat", follow_redirects=False)
    assert rv.status_code == 200
    assert b"Enter your email" not in rv.data

    client.get("/logout", follow_redirects=True)
    rv = client.post("/login", data={
        "email": "test@example.com",
        "password": "secret12",
    }, follow_redirects=True)
    assert rv.status_code == 200
    assert b"Choose Your Focus Area" in rv.data

    rv = client.get("/home", follow_redirects=False)
    assert rv.status_code == 200
    assert b"Choose Your Focus Area" in rv.data


def test_login_invalid(client):
    rv = client.post("/login", data={
        "email": "nobody@example.com",
        "password": "wrong",
    })
    assert b"Invalid email or password" in rv.data


def test_dashboard_requires_auth(client):
    rv = client.get("/dashboard", follow_redirects=True)
    assert rv.status_code == 200
    assert b"Log In" in rv.data or b"Enter your email" in rv.data


def test_auth_survives_without_session_cookie(client):
    """Durable twin_mate_uid alone must keep protected pages working."""
    client.post("/signup", data={
        "email": "cookieonly@example.com",
        "password": "secret12",
    })
    client.delete_cookie("twin_mate_session")
    client.delete_cookie("remember_token")

    rv = client.get("/dashboard", follow_redirects=False)
    assert rv.status_code == 200
    assert b"Welcome Back" not in rv.data
    assert b"Enter your email" not in rv.data


def test_forgot_and_reset_password(client):
    client.post("/signup", data={
        "email": "resetme@example.com",
        "password": "oldpass1",
    }, follow_redirects=True)
    client.get("/logout", follow_redirects=True)

    rv = client.get("/forgot-password")
    assert rv.status_code == 200
    assert b"Forgot Password" in rv.data

    rv = client.post("/forgot-password", data={"email": "resetme@example.com"}, follow_redirects=True)
    assert rv.status_code == 200
    assert b"reset-password/" in rv.data

    # Extract token from shown local reset link
    import re
    m = re.search(rb"/reset-password/([^\"'\s<]+)", rv.data)
    assert m
    token = m.group(1).decode()

    rv = client.post(f"/reset-password/{token}", data={
        "password": "newpass1",
        "confirm_password": "newpass1",
    }, follow_redirects=True)
    assert rv.status_code == 200
    assert b"Password updated" in rv.data or b"Log In" in rv.data

    # Old password fails
    rv = client.post("/login", data={
        "email": "resetme@example.com",
        "password": "oldpass1",
    }, follow_redirects=True)
    assert b"Invalid email or password" in rv.data

    # New password works
    rv = client.post("/login", data={
        "email": "resetme@example.com",
        "password": "newpass1",
    }, follow_redirects=True)
    assert b"Choose Your Focus Area" in rv.data
