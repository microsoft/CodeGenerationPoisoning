#!/usr/bin/python
# -*- coding: utf-8 -*-
# __author__ = "Albin TCHOPBA"
# __copyright__ = "Copyright 2020 Albin TCHOPBA and contributors"
# __credits__ = ["Albin TCHOPBA and contributors"]
# __license__ = "GPL"
# __version__ = "3"
# __maintainer__ = "Albin TCHOPBA"
# __email__ = "Albin TCHOPBA <atchopba @ gmail dot com"
# __status__ = "Production"

from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import login_user, current_user
from flask import current_app
from .models import User
from .core.db.user import EUser, TUser
from . import login_manager

#
auth_bp = Blueprint("auth_bp", 
                    __name__, 
                    template_folder="templates", 
                    static_folder="static")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main_bp.home'))  # Bypass if user is logged in
    if request.method == "POST":
        login_ = request.form["login"]
        mdp_ = request.form["mdp"]
        ruser = EUser().get_by_user(TUser(login_, mdp_, None))
        if ruser:
            l_user = User()
            l_user.id = ruser.login
            dbclient = {"DATABASE_CLIENT" : ruser.db}
            current_app.config.update(dbclient)
            login_user(l_user)
            return redirect(url_for('main_bp.home'))
        else:
            return render_template("auth/login.html", error="Login/mot de passe erronée! Veuillez recommencer")
    return render_template("auth/login.html")

@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    return render_template("auth/signup.html")

@login_manager.user_loader
def load_user(user_id):
    if user_id is not None:
        ruser = EUser().get_by_login(user_id)
        user_ = User()
        user_.id = ruser.login
        dbclient = {"DATABASE_CLIENT" : ruser.db}
        current_app.config.update(dbclient)
        return user_ 
    return None

@login_manager.unauthorized_handler
def unauthorized():
    return redirect(url_for('auth_bp.login'))