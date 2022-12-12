# -*- coding: utf-8 -*-
"""Authentication endpoints and control."""
from flask import flash, redirect, render_template, request, url_for
from flask_login import login_required, logout_user

from app.auth.form import RegisterForm
from app.blueprints import auth_user
from app.extension import login_manager
from app.models.user import User
from app.util import flash_errors


@login_manager.user_loader
def load_user(user_id):
    """Load user by ID."""
    return User.get_by_id(int(user_id))


@auth_user.route("/logout/")
@login_required
def logout():
    """Logout."""
    logout_user()
    flash("You are logged out.", "info")
    return redirect(url_for("homepage.index.home"))


@auth_user.route("/register/", methods=["GET", "POST"])
def register():
    """Register new user."""
    form = RegisterForm(request.form)
    if form.validate_on_submit():
        User.create(
            username=form.username.data,
            email=form.email.data,
            password=form.password.data,
            active=True,
        )
        flash("Thank you for registering. You can now log in.", "success")
        return redirect(url_for("homepage.index.home"))
    else:
        flash_errors(form)
    return render_template("register.html", form=form)
