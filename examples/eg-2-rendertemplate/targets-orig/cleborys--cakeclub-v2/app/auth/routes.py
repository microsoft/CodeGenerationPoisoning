from flask import render_template, flash, redirect, url_for, current_app
from flask_login import current_user, login_user, logout_user
from app import db
from app.auth import blueprint
import app.clubsessions as clubsessions
from app.auth.forms import (
    LoginForm,
    RegistrationForm,
    RequestPasswordResetForm,
    PasswordResetForm,
)
from app.auth.mail import send_password_reset_email
import app.users as users


@blueprint.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("lobby.lobby"))
    form = LoginForm()
    if form.validate_on_submit():
        user = users.get_user_by_email(form.email.data)
        if user is None or not user.check_password(form.password.data):
            flash("We could not find a user with that name and password.")
            return redirect(url_for("auth.login"))
        login_user(user, remember=form.remember_me.data)
        current_app.logger.info(f"Logged in user {user}")
        return redirect(url_for("lobby.lobby"))
    return render_template("login.html", title="Sign In", form=form)


@blueprint.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("lobby.lobby"))


@blueprint.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("lobby.lobby"))
    form = RegistrationForm()
    if form.validate_on_submit():
        if form.registration_token.data != current_app.config["REGISTRATION_KEY"]:
            flash(f"Your registration token was invalid")
            return redirect(url_for("auth.register"))
        user_dict = dict(username=form.username.data, email=form.email.data)
        user = users.create(user_dict, form.password.data)
        clubsessions.join_all_future_sessions(user)
        flash("Thank you for signing up!")
        login_user(user)
        return redirect(url_for("lobby.lobby"))
    return render_template("register.html", title="Sign Up", form=form)


@blueprint.route("/request_password_reset", methods=["GET", "POST"])
def request_password_reset():
    if current_user.is_authenticated:
        return redirect(url_for("lobby.lobby"))

    form = RequestPasswordResetForm()
    if form.validate_on_submit():
        user = users.get_user_by_email(form.email.data)
        if user is not None:
            send_password_reset_email(user)
        flash("We sent you an email to reset your password!")
        return redirect(url_for("auth.login"))

    return render_template(
        "request_password_reset.html", title="Reset My Password", form=form
    )


@blueprint.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("lobby.lobby"))

    user = users.verify_password_reset_token(token)
    if not user:
        return redirect(url_for("lobby.lobby"))

    form = PasswordResetForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash("You successfully reset your password.")
        return redirect(url_for("auth.login"))

    return render_template("reset_password.html", title="Reset My Password", form=form)
