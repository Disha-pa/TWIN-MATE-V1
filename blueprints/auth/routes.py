from flask import flash, make_response, redirect, render_template, request, url_for
from flask_login import current_user

from blueprints.auth import auth_bp
from services.auth_service import (
    authenticate,
    create_account,
    create_password_reset_token,
    reset_password_with_token,
)
from services.notification_service import send_email
from services.stats_service import get_user_goals
from utils.auth import apply_auth_cookie, login_user, logout_user, normalize_email


def _show_home(message):
    """
    Show Home in THIS response (status 200, no redirect).
    Also attach the durable login cookie on this same response.
    """
    flash(message, "success")
    goals = get_user_goals(current_user.id)
    html = render_template("home.html", has_goals=bool(goals.get("goals")))
    resp = make_response(html)
    resp.headers["Cache-Control"] = "no-store"
    return apply_auth_cookie(resp)


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return _show_home("Welcome back!")

    if request.method == "POST":
        email_raw = request.form.get("email", "")
        password = request.form.get("password", "")
        user, error = create_account(email_raw, password)
        if error:
            flash(error, "error")
            return render_template("signup.html", email=email_raw)

        login_user(user, remember=True)
        return _show_home("Account created! Welcome.")

    return render_template("signup.html", email="")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return _show_home("Welcome back!")

    if request.method == "POST":
        email_raw = request.form.get("email", "")
        password = request.form.get("password", "")
        user, error = authenticate(email_raw, password)
        if error:
            flash(error, "error")
            return render_template("login.html", email=email_raw)

        login_user(user, remember=True)
        return _show_home("Welcome back!")

    return render_template("login.html", email="")


@auth_bp.route("/logout")
def logout():
    logout_user()
    flash("Logged out.", "success")
    return redirect(url_for("landing"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if current_user.is_authenticated:
        return _show_home("Welcome back!")

    if request.method == "POST":
        email_raw = request.form.get("email", "")
        token, message = create_password_reset_token(email_raw)
        reset_link = None

        if token:
            reset_link = url_for("auth.reset_password", token=token, _external=True)
            send_email(
                normalize_email(email_raw),
                "Twin Mate — Reset your password",
                (
                    "<p>Hi,</p>"
                    "<p>Click the link below to reset your Twin Mate password "
                    "(valid for 1 hour):</p>"
                    f'<p><a href="{reset_link}">{reset_link}</a></p>'
                    "<p>If you did not request this, you can ignore this email.</p>"
                ),
            )

        flash(message, "success" if "valid email" not in message.lower() else "error")
        return render_template(
            "forgot_password.html",
            email=email_raw,
            reset_link=reset_link,
        )

    return render_template("forgot_password.html", email="", reset_link=None)


@auth_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return _show_home("Welcome back!")

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("reset_password.html", token=token)

        ok, message = reset_password_with_token(token, password)
        flash(message, "success" if ok else "error")
        if ok:
            return redirect(url_for("auth.login"))
        return render_template("reset_password.html", token=token)

    return render_template("reset_password.html", token=token)
