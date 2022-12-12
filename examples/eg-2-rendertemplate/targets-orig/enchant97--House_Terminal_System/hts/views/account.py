from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..database.dao.exceptions import RowAlreadyExists
from ..database.dao.user import (change_user_password, get_api_key,
                                 new_account, update_usersettings)
from ..helpers.calculations import html_date
from ..helpers.checkers import is_admin

account = Blueprint("account", __name__)


@account.route("/newaccount", methods=["POST", "GET"])
@login_required
def newaccount():
    if is_admin(current_user.username):
        if request.method == "POST":
            username = request.form.get("username")
            password = request.form.get("password")
            birthday = request.form.get("birthday", type=html_date)
            if username and password and birthday:
                try:
                    new_account(username, password, birthday)
                    flash("user created!")
                except RowAlreadyExists:
                    flash("user already exists!", "error")
            else:
                flash("missing required form details", "error")
        return render_template("account/new_account.html")
    return redirect(url_for("main.index"))


@account.route("/changepassword", methods=["POST", "GET"])
@login_required
def changepassword():
    if request.method == "POST":
        old_password = request.form.get("old_password")
        new_password = request.form.get("new_password")
        if old_password and new_password:
            if change_user_password(current_user.id_, new_password, old_password):
                flash("password changed")
            else:
                flash("password could not be changed", "error")
        else:
            flash("missing required form details", "error")
    return render_template("account/change_password.html")


@account.route("/usersettings", methods=["GET", "POST"])
@login_required
def settings():
    user_id = current_user.id_
    api_key = get_api_key(user_id).key
    if request.method == "POST":
        rem_notif = request.form.get("rem_notif", False, bool)
        fm_notif = request.form.get("fm_notif", False, bool)
        mess_notif = request.form.get("mess_notif", False, bool)
        user_setting = update_usersettings(
            user_id, rem_notif, fm_notif, mess_notif)
        flash("updated your settings")
    else:
        user_setting = update_usersettings(user_id)
    return render_template(
        "account/user_settings.html",
        the_settings=user_setting, api_key=api_key)
