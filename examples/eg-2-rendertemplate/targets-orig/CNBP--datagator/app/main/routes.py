from datetime import datetime
from flask import (
    render_template,  # flask function to render a HTML template with elements replaced.
    flash,  # show a message overlay.
    redirect,  # redirect to another page.
    url_for,  # used to interpret endpoints.
    request,
    current_app,  # to get current app related issue.
)
from flask_login import (  # flask_login module is a module to help manage module
    current_user,  # get the active logged in user.
    login_required,  # used to @login_required decorator to indicate a route MUST be logged in before showing.
)

from app import db
from app.main.forms import EditProfileForm, PostForm

from app.models import (
    User,
    Entry,
)  # import data base model for User and Post construct.
from app.main import bp


"""
This file is responsible for ROUTING the VIEW functions. What happens when you look at a page etc?

Any view needs to be defined here. 

"""

import logging

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO)

# index page rout.
@bp.route(
    "/", methods=["GET", "POST"]
)  # this indicate which endpoint these actions will be carried out.
@bp.route(
    "/index", methods=["GET", "POST"]
)  # this indicate which endpoint these actions will be carried out.
@login_required  # this marks the page as login required.
def index():

    # Get the page argumetn from the URL entered. Default to 1?
    page = request.args.get("page", 1, type=int)
    user_current = User.query.filter_by(username=current_user.username).first()
    # Use the paginate function from SQLAlchemy to get the posts.
    entries = Entry.query.filter_by(user_id=user_current.id).paginate(
        page, current_app.config["POSTS_PER_PAGE"], False
    )

    # Next URL if they exist.
    next_url = (
        url_for("main.index", page=entries.next_num) if entries.has_next else None
    )

    # Previous URL if they exist
    prev_url = (
        url_for("main.index", page=entries.prev_num) if entries.has_prev else None
    )

    # Return rendered template with the variables set.
    # Post > Redirect > Get pattern.
    return render_template(
        "index.html",
        title="Home, Sweet Home!",
        entries=entries.items,  # must use ITEMS if using pagination
        next_url=next_url,
        prev_url=prev_url,
    )


@bp.route("/user/<username>")
@login_required
def user(username):
    """
    This shows the information for the relevant username.
    :param username:
    :return:
    """
    # set user
    user = User.query.filter_by(username=username).first_or_404()

    # set current pagination limit
    page = request.args.get("page", 1, type=int)

    posts = user.posts.order_by(Post.timestamp.desc()).paginate(
        page, current_app.config["POSTS_PER_PAGE"], False
    )

    next_url = (
        url_for("user", username=user.username, page=posts.next_num)
        if posts.has_next
        else None
    )
    prev_url = (
        url_for("user", username=user.username, page=posts.prev_num)
        if posts.has_prev
        else None
    )

    # Post > Redirect > Get pattern.
    return render_template(
        "user.html", user=user, posts=posts.items, next_url=next_url, prev_url=prev_url
    )


@bp.before_request
def before_request():
    """
    This is executed every time before a view request happen, put something that required logging here typically
    :return:
    """
    # If authenticated
    if current_user.is_authenticated:

        # Set the date column value to this.
        current_user.last_seen = datetime.utcnow()

        # Commit the information to the database.
        db.session.commit()


@bp.route("/edit_profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    """
    This allows editing of the profile.
    """

    # Instantiate the form
    form = EditProfileForm(current_user.username)

    # If past validation, during submission,
    if form.validate_on_submit():

        # assign username, about me info
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash("Your changes have been saved.")
        return redirect(url_for("main.edit_profile"))

    # if it is just to get data, load from database.
    elif request.method == "GET":
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me

    return render_template("edit_profile.html", title="Edit Profile", form=form)


@bp.route("/follow/<username>")
@login_required
def follow(username):
    """
    Follow a user provided by the username.
    :param username:
    :return:
    """
    # Check against the database.
    user = User.query.filter_by(username=username).first()

    # If doesn't exist,
    if user is None:
        flash(f"User {username} not found.")
        return redirect(url_for("main.index"))
    # If it is current user.
    if user == current_user:
        flash("You cannot follow yourself!")
        return redirect(url_for("main.user", username=username))

    # Commit change to database.
    current_user.follow(user)
    db.session.commit()

    # flash and redirect.
    flash("You are following {username}!")
    return redirect(url_for("main.user", username=username))


@bp.route("/unfollow/<username>")
@login_required
def unfollow(username):
    """
    Unfollow a particular user.
    :param username:
    :return:
    """
    # Check against the database.
    user = User.query.filter_by(username=username).first()

    # If it doesn't exist
    if user is None:
        flash(f"User {username} not found.")
        return redirect(url_for("main.index"))

    # if it is the user,
    if user == current_user:
        flash("You cannot unfollow yourself!")
        return redirect(url_for("main.user", username=username))

    # unfollow user and commit to database.
    current_user.unfollow(user)
    db.session.commit()
    flash("You are not following {username}")
    return redirect(url_for("main.user", username=username))


@bp.route("/explore")
@login_required
def explore():
    """
    Explore the global posts stream
    :return:
    """
    # Default page argumet is 1. Otherwise, based
    page = request.args.get("page", 1, type=int)

    posts = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, current_app.config["POSTS_PER_PAGE"], False
    )
    next_url = url_for("main.explore", page=posts.next_num) if posts.has_next else None
    prev_url = url_for("main.explore", page=posts.prev_num) if posts.has_prev else None

    return render_template(
        "index.html",
        title="Explore",
        posts=posts.items,  # this must include ITEMS when using pagination
        prev_url=prev_url,
        next_url=next_url,
    )
