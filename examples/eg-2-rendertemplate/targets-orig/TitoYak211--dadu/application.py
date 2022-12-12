import os

from flask import Flask, session, render_template, request, flash
from flask_session import Session
from helpers import *
from model import *

app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
Session(app)

@app.before_first_request
def create_tables():
    db.create_all()

@app.route("/", methods=["GET"])
@login_required
def index():
    """Show homepage"""
    if session["user_id"] is None:
        return login()

    else:
        return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Ensure password and confirmation match
        elif not request.form.get("password") == request.form.get("confirmation"):
            return apology("passwords do not match", 400)

        user = User.query.filter_by(username=request.form.get("username")).first()
        
        # unique username constraint violated?
        if user:
            return apology("username taken", 400)

        # create new user
        new_user = User(username = request.form.get("username"), password = request.form.get("password"))

        db.session.add(new_user)
        db.session.commit()

        # get current user
        user = User.query.filter_by(username=request.form.get("username")).first()

        # Remember which user has logged in
        session["user_id"] = user.id

        # Display a flash message
        flash("Registered!")

        # Redirect user to home page
        return redirect("/")

    # else if user reached route via GET
    else:
        return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        user = User.query.filter_by(username=request.form.get("username")).all()

        # Ensure username exists and password is correct
        if len(user) != 1:
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = user[0].id

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")