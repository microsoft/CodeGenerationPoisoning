from flask import (Blueprint, current_app, flash, redirect, render_template,
                   request, url_for)
from flask_login import current_user, login_required, login_user, logout_user

from ..database import dao
from ..helpers.checkers import is_admin

main = Blueprint("main", __name__)


@main.route("/", methods=["POST", "GET"])
def index():
    if current_user.is_authenticated:
        return redirect(url_for("home.dashboard"))
    return render_template("main/index.html", users=dao.user.get_users())


@main.route("/about")
def about():
    return render_template("main/about.html")


@main.route("/login", methods=["POST"])
def do_login():
    if current_user.is_authenticated:
        return redirect(url_for("home.dashboard"))
    username = request.form.get("username")
    password = request.form.get("password")
    remember_me = request.form.get("rememberme", False)
    if not username or not password:
        flash("You have left the form blank", "warning")
    user = dao.user.try_login_user(username, password)
    if user:
        if remember_me:
            login_user(user, remember=True)
        else:
            login_user(user, remember=False)
        return redirect(url_for("home.dashboard"))
    flash("username or password not correct", "warning")
    return redirect(url_for(".index"))


@main.route("/logout")
@login_required
def do_logout():
    logout_user()
    flash("You have now logged out")
    return redirect(url_for(".index"))


@main.route("/idle-display")
@login_required
def idle_display():
    return render_template("main/idle-display.html")


@main.route("/cleanup-db")
@login_required
def cleanup_db():
    if is_admin(current_user.username):
        current_app.logger.info(
            "start permanent deletion of rows marked for removal")
        dao.reminder.delete_removed()
        dao.photo_manager.delete_removed()
        dao.inventory_manager.delete_removed()
        dao.freezer_manager.delete_removed()
        dao.dashboard.delete_removed()
        dao.user.delete_removed()
        current_app.logger.info(
            "finished permanent deletion of rows marked for removal")
        flash("Finished cleanup")
    else:
        flash("You will need to be a admin to do that", "error")
    return redirect(url_for("home.dashboard"))
