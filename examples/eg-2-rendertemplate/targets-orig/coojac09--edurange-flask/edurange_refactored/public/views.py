# -*- coding: utf-8 -*-
"""Public section, including homepage and signup."""
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from jwt import JWT
from jwt.exceptions import JWTDecodeError

from edurange_refactored.extensions import bcrypt, login_manager
from edurange_refactored.public.forms import (
    LoginForm,
    RequestResetPasswordForm,
    RestorePasswordForm,
)
from edurange_refactored.tasks import test_send_async_email
from edurange_refactored.user.forms import RegisterForm
from edurange_refactored.user.models import GroupUsers, StudentGroups, User
from edurange_refactored.utils import TokenHelper, flash_errors

blueprint = Blueprint("public", __name__, static_folder="../static")
jwtToken = JWT()
helper = TokenHelper()
oct_data = helper.get_data()


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID."""
    return User.get_by_id(int(user_id))


@blueprint.route("/", methods=["GET", "POST"])
def home():
    """Home page."""
    form = LoginForm(request.form)
    current_app.logger.info("Hello from the home page!")
    # Handle logging in
    if request.method == "POST":
        if form.validate_on_submit():
            login_user(form.user)
            flash("You are logged in.", "success")
            redirect_url = url_for("public.home")
            return redirect(redirect_url)
        else:
            flash_errors(form)
    return render_template("public/home.html", form=form)


@blueprint.route("/reset/", methods=["GET", "POST"])
def reset_password():
    """Reset password."""
    if current_user.is_authenticated:
        return redirect(url_for("public.home"))
    form = RequestResetPasswordForm(request.form)
    if request.method == "POST":
        if not form.validate_on_submit():
            flash("Unknown email address.", "warning")
            return render_template("public/request_reset_password.html", form=form)
        else:
            email_data = form.get_email_data()
            test_send_async_email(email_data)
            flash("Please check your email to reset your password.", "success")
            return redirect(url_for("public.home"))
    return render_template("public/request_reset_password.html", form=form)


@blueprint.route("/restore/<tk>", methods=["GET", "POST"])
def restore_password(tk):
    if current_user.is_authenticated:
        return redirect(url_for("public.home"))
    try:
        decoded_token = jwtToken.decode(
            tk, oct_data, do_verify=True, do_time_check=True
        )
    except JWTDecodeError:
        flash("Password reset link has expired.", "warning")
        return redirect(url_for("public.home"))
    user = User.query.filter_by(email=decoded_token["email"]).first()
    if not user:
        flash("Can't find any matching user.", "warning")
        return render_template("public/home")
    form = RestorePasswordForm(request.form)
    if not form.validate_on_submit():
        # flash("Unable to update your password, please type in your password again.", "warning")
        return render_template(
            "public/restore_password.html", form=form, email=decoded_token["email"]
        )
    else:
        User.update(
            self=user, password=bcrypt.generate_password_hash(form.password.data)
        )
        flash("Password updated.", "success")
    return redirect(url_for("public.home"))


@blueprint.route("/logout/")
@login_required
def logout():
    """Logout."""
    session.pop("viewMode", None)
    logout_user()
    flash("You are logged out.", "info")
    return redirect(url_for("public.home"))


@blueprint.route("/register/", methods=["GET", "POST"])
def register():
    """Register new user."""
    if current_user.is_authenticated:
        return redirect(url_for("public.home"))
    form = RegisterForm(request.form)
    if form.validate_on_submit():
        User.create(
            username=form.username.data,
            email=form.email.data,
            password=form.password.data,
            active=True,
        )
        if form.code.data:
            group = StudentGroups.query.filter_by(code=form.code.data).first()
            user = User.query.filter_by(username=form.username.data).first()
            gid = group.get_id()
            uid = user.get_id()
            GroupUsers.create(user_id=uid, group_id=gid)
        else:
            group = StudentGroups.query.filter_by(name="ALL").first()
            gid = group.get_id()
            user = User.query.filter_by(username=form.username.data).first()
            uid = user.get_id()
            GroupUsers.create(user_id=uid, group_id=gid)
        flash("Thank you for registering. You can now log in.", "success")
        return redirect(url_for("public.home"))
    else:
        flash_errors(form)
    return render_template("public/register.html", form=form)


@blueprint.route("/about/")
def about():
    """About page."""
    form = LoginForm(request.form)
    return render_template("public/about.html", form=form)
