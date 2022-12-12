from flask import Blueprint, render_template

website = Blueprint("website", __name__)


@website.route("/")
def homepage():
    return render_template("index.html")


@website.route("/login")
def login():
    return render_template("login.html")


@website.route("/create-account")
def create_account():
    return render_template("create_account.html")


@website.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")
