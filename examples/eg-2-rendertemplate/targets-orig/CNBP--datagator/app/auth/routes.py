from flask import (
    render_template,  # flask function to render a HTML template with elements replaced.
    redirect,  # redirect to another page.
    url_for,  # used to interpret endpoints.
    flash,  # show a message overlay.
    request,
)
from werkzeug.urls import url_parse
from flask_login import (  # flask_login module is a module to help manage module
    login_user,  # login the user action.
    logout_user,  # used to logout user
    current_user,  # get the active logged in user.
)

from app.auth.forms import (
    LoginForm,  # our project customary forms built here to carry out login function.
    RegistrationForm,  # our project customary forms built here to carry out login function.
    ResetPasswordRequestForm,  # the form that can REQUEST the reset the password
    ResetPasswordForm,  # the form that is actually resetting the password
)


from app import db
from app.auth import bp

from app.models import User  # import data base model for User and Post construct.

from datetime import datetime
from app.auth.email import send_password_reset_email


"""
This file is responsible for ROUTING the VIEW functions. What happens when you look at a page etc?

Any view needs to be defined here. 

"""

import logging

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO)


@bp.route("/logout")
def logout():
    """
    End point to log out the user
    :return:
    """
    logout_user()  # from the flask_login module
    return redirect(url_for("main.index"))


@bp.route("/register", methods=["GET", "POST"])
def register():
    """
    View function for the registration page.
    :return:
    """
    # Redirect to index if the user is already logged in.
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = RegistrationForm()

    # First, ensure the information contained in the form pass the validation phase.
    if form.validate_on_submit():

        # Create the user based on the data provided.
        user = User(username=form.username.data, email=form.email.data)
        # Set the password field entry.
        user.set_password(form.password.data)

        # Commit the information to the database.
        db.session.add(user)
        db.session.commit()

        # Inform the user.
        flash("Congratulations, you are now a registered user!")
        # Redirect to login.
        return redirect(url_for("auth.login"))

    # if form not valid, redirect to register page.
    return render_template("auth/register.html", title="Register", form=form)


@bp.route("/login", methods=["GET", "POST"])
def login():
    """
    The login endpoint.
    :return:
    """
    # Instantiate form data object.
    form = LoginForm()

    # Deal with when visiting index when already authenticated.
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    form = LoginForm()

    if form.validate_on_submit():

        # query User table from the database using the user name.
        # Will return NONE if it doesn't exist.
        user = User.query.filter_by(username=form.username.data).first()

        # Reject if no user or wrong password.
        if user is None or not user.check_password(form.password.data):
            flash("Invalid username or password")
            # Redirect to login to retry again.
            return redirect(url_for("auth.login"))

        # Login the actual user.
        login_user(user, remember=form.remember_me.data)

        # Flash warning required.
        flash(
            f"Welcome, User {form.username.data}, you have asked to rememebr you? {form.remember_me.data}"
        )

        # If the login URL includes a next argument that is set to a relative path (or in other words, a URL without the domain portion), then the user is redirected to that URL.
        next_page = request.args.get("next")

        # If the login URL does not have a next argument, then the user is redirected to the index page.
        if not next_page:
            next_page = url_for("main.index")

        # If the login URL includes a next argument that is set to a full URL that includes a domain name, then the user is redirected to the index page.
        if url_parse(next_page).netloc != "":
            next_page = url_for("main.index")

        # Redirect to a page should the form pass validation.
        return redirect(next_page)

    return render_template("auth/login.html", title="Sign In", form=form)


@bp.route("/reset_password_request", methods=["GET", "POST"])
def reset_password_request():
    """
    Page where user can request the reset of the password
    :return:
    """
    # if logged in, return to index.
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    # Instantiate the form object.
    form = ResetPasswordRequestForm()

    # if form validate successfully,
    if form.validate_on_submit():

        # Get user by email.
        user = User.query.filter_by(email=form.email.data).first()

        # if user EXIST, send email.
        if user:
            send_password_reset_email(user)

        # Display to inform user.
        flash("Check your email for the instruction to reset your password")

        # Redirect to login.
        return redirect(url_for("auth.login"))

    return render_template(
        "auth/reset_password_request.html", title="Reset Password", form=form
    )


@bp.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """
    View function of actual form to reset the password by setting it on the page.
    :param token:
    :return:
    """
    # Reject when already authenticated.
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    # verify the token to get the username.
    user = User.verify_reset_password_token(token)

    # if None (i.e. bad token) do not proceed.
    if not user:
        return redirect(url_for("main.index"))

    # Instantiate resetpassword form.
    form = ResetPasswordForm()

    # if the form is valid,
    if form.validate_on_submit():

        # set the password for this user.
        user.set_password(form.password.data)

        # push to data base.
        db.session.commit()

        flash("Your password has been reset.")

        return redirect(url_for("auth.login"))

    return render_template("auth/reset_password.html", form=form)
