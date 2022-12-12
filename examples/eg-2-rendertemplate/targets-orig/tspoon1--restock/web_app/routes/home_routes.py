# web_app/routes/home_routes.py

from flask import Blueprint, render_template, flash, redirect, request
from app.restock import addNewRow, initSheet

home_routes = Blueprint("home_routes", __name__)

@home_routes.route("/")
def index():
    print("VISITED THE HOME PAGE...")
    return render_template("home.html")

@home_routes.route("/submit", methods=["POST"])
def handleSubmit():
    print("FORM DATA:", dict(request.form))
    submission = dict(request.form)
    row = [submission['email'], submission['link']]
    initSheet()
    addNewRow(row)
    return redirect("/")

@home_routes.route("/about")
def about():
    print("VISITED THE ABOUT PAGE...")
    return render_template("about.html")
