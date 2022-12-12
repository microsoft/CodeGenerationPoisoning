# -*- coding: utf-8 -*-
"""Routes included here.

/                   the application homepage

/about/             standard about page

/contributors/      information about contributors or how to begin contributing
"""
from flask import current_app, flash, redirect, render_template, request, url_for
from flask_login import login_user

from app.auth.form import LoginForm
from app.blueprints import homepage_index
from app.util import flash_errors


@homepage_index.route("/", methods=["GET", "POST"])
def home():
    """Home page."""
    form = LoginForm(request.form)
    current_app.logger.info("Hello from the home page!")
    # Handle logging in
    if request.method == "POST":
        if form.validate_on_submit():
            login_user(form.user)
            flash("Successfully logged in.", "success")
            redirect_url = request.args.get("next") or url_for("user.profile.account")
            return redirect(redirect_url)
        else:
            flash_errors(form)
    return render_template("home.html", form=form)


@homepage_index.route("/about/")
def about():
    """Application "About" page."""
    form = LoginForm(request.form)
    return render_template("about.html", form=form)


@homepage_index.route("/contributors/")
def contributors():
    """Application contributors page."""
    form = LoginForm(request.form)
    return render_template("contributors.html", form=form)
