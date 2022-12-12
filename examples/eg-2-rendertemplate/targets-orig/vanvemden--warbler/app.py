import os

from flask import Flask, render_template, request, flash, redirect, session, g
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError

from forms import UserAddForm, UserEditForm, LoginForm, MessageForm, UserPasswordForm
from models import db, connect_db, User, Message, Likes

CURR_USER_KEY = "curr_user"

app = Flask(__name__)

# Get DB_URI from environ variable (useful for production/testing) or,
# if not set there, use development local db.
app.config['SQLALCHEMY_DATABASE_URI'] = (os.environ.get(
    'DATABASE_URL', 'postgres:///warbler'))

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = True
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "it's a secret")
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
toolbar = DebugToolbarExtension(app)

connect_db(app)

##############################################################################
# User signup/login/logout


@app.errorhandler(404)
def error_page(e):
    return render_template('404.html')


@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])
        g.message_form = MessageForm()
    else:
        g.user = None


def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Logout user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]


@app.route('/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, present form.

    If the there already is a user with that username: flash message
    and re-present form.
    """

    form = UserAddForm()

    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
                image_url=form.image_url.data or User.image_url.default.arg,
            )
            db.session.commit()

        except IntegrityError:
            flash("Username already taken", 'danger')
            return render_template('users/signup.html', form=form)

        do_login(user)

        return redirect("/")

    else:
        return render_template('users/signup.html', form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login."""

    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(form.username.data, form.password.data)

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", 'danger')

    return render_template('users/login.html', form=form)


@app.route('/logout')
def logout():
    """Handle logout of user."""
    if CURR_USER_KEY in session:
        do_logout()
        flash("You have been logged out successfully!", "success")

    return redirect('/login')


##############################################################################
# General user routes:


@app.route('/users')
def list_users():
    """Page with listing of users.

    Can take a 'q' param in querystring to search by that username.
    """

    search = request.args.get('q')

    if not search:
        users = User.query.all()
    else:
        users = User.query.filter(User.username.like(f"%{search}%")).all()

    return render_template('users/index.html', users=users)


@app.route('/users/<int:user_id>')
def users_show(user_id):
    """Show user profile."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)

    # snagging messages in order from the database;
    # user.messages won't be in order by default
    messages = (Message.query.filter(Message.user_id == user_id).order_by(
        Message.timestamp.desc()).limit(100).all())
    return render_template('users/show.html', user=user, messages=messages)


@app.route('/users/<int:user_id>/following')
def show_following(user_id):
    """Show list of people this user is following."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template('users/following.html', user=user)


@app.route('/users/<int:user_id>/followers')
def users_followers(user_id):
    """Show list of followers of this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    return render_template('users/followers.html', user=user)


@app.route('/users/follow/<int:follow_id>', methods=['POST'])
def add_follow(follow_id):
    """Add a follow for the currently-logged-in user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_user = User.query.get_or_404(follow_id)
    g.user.following.append(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/stop-following/<int:follow_id>', methods=['POST'])
def stop_following(follow_id):
    """Have currently-logged-in-user stop following this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_user = User.query.get(follow_id)
    if followed_user in g.user.following:
        g.user.following.remove(followed_user)
        db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/profile/password', methods=["GET", "POST"])
def change_password():

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = UserPasswordForm()

    if form.validate_on_submit():
        password = form.password.data

        if User.authenticate(password=password, username=g.user.username):

            if form.new_password.data == form.confirm_password.data:
                g.user.password = User.change_password(
                    password=form.new_password.data)

                db.session.commit()
                flash("Your password has been updated successfully.",
                      "success")
                return redirect(request.referrer)
            else:
                flash('Sorry, but your two new inputs did not match!')
                return render_template("users/password.html", form=form)
        else:
            flash("Please enter the correct password to update your profile.",
                  "danger")
            return render_template("users/password.html", form=form)
    else:
        return render_template("users/password.html", form=form)


@app.route('/users/profile', methods=["GET", "POST"])
def profile():
    """Update profile for current user.
       Check if the correct password has been entered.
       TODO: Check if username and email are unique.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = UserEditForm(obj=g.user)

    if form.validate_on_submit():
        password = form.password.data

        if User.authenticate(password=password, username=g.user.username):
            g.user.username = form.username.data
            g.user.email = form.email.data
            g.user.image_url = form.image_url.data
            g.user.header_image_url = form.header_image_url.data
            g.user.bio = form.bio.data

            db.session.commit()
            flash("Your profile has been updated successfully.", "success")
            return redirect(f"/users/{ g.user.id }")
        else:
            flash("Please enter the correct password to update your profile.",
                  "danger")
            return render_template("users/edit.html", form=form)
    else:
        return render_template("users/edit.html", form=form)


@app.route('/users/delete', methods=["POST"])
def delete_user():
    """Delete user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    do_logout()

    db.session.delete(g.user)
    db.session.commit()

    return redirect("/signup")


##############################################################################
# Messages routes:


def serialize_message(message, like):
    return {
        'id': message.id,
        'text': message.text,
        'timestamp': message.timestamp,
        'user_id': message.user_id,
        'like': like,
    }


@app.route('/messages/new', methods=["GET", "POST"])
def messages_add():
    """Add a message:

    Show form if GET. If valid, update message and redirect to user page.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    text = request.json['text']

    if text:
        msg = Message(text=text, user_id=g.user.id)
        db.session.add(msg)
        db.session.commit()
        return ({"message": serialize_message(msg, False)}, 201)

    return render_template('messages/new.html', form=form)


@app.route('/messages/<int:message_id>', methods=["GET"])
def messages_show(message_id):
    """Show a message."""

    msg = Message.query.get(message_id)
    return render_template('messages/show.html', message=msg)


@app.route('/messages/<int:message_id>/like', methods=["GET", "POST"])
def add_like(message_id):

    message = Message.query.get(message_id)
    if message.user_id == g.user.id:
        return ({'message': "Can't like your own message"})

    if message in g.user.likes:
        g.user.likes = [
            like for like in g.user.likes if not like.id == message_id
        ]
        like = False
    else:
        g.user.likes.append(message)
        like = True

    db.session.commit()

    return ({'message': serialize_message(message, like)})


@app.route('/users/<int:id>/likes')
def show_favorites(id):
    user = User.query.get_or_404(id)
    likes = user.likes
    return render_template('likes.html', messages=likes, user=user)


@app.route('/messages/<int:message_id>/delete', methods=["POST"])
def messages_destroy(message_id):
    """Delete a message."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    msg = Message.query.get(message_id)
    db.session.delete(msg)
    db.session.commit()

    return redirect(f"/users/{g.user.id}")


##############################################################################
# Homepage and error pages


@app.route('/')
def homepage():
    """Show homepage:

    - anon users: no messages
    - logged in: 100 most recent messages of followed_users
    """

    if g.user:
        following_ids = {f.id for f in g.user.following}
        following_ids.add(g.user.id)

        messages = (Message.query.filter(
            Message.user_id.in_(following_ids)).order_by(
                Message.timestamp.desc()).limit(100).all())

        liked_msg_ids = [msg.id for msg in g.user.likes]

        return render_template('home.html',
                               messages=messages,
                               likes=liked_msg_ids)

    else:
        messages = (Message.query.order_by(
            Message.timestamp.desc()).limit(5).all)

        return render_template('home-anon.html', messages=messages)


##############################################################################
# Turn off all caching in Flask
#   (useful for dev; in production, this kind of stuff is typically
#   handled elsewhere)
#
# https://stackoverflow.com/questions/34066804/disabling-caching-in-flask


@app.after_request
def add_header(req):
    """Add non-caching headers on every request."""

    req.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    req.headers["Pragma"] = "no-cache"
    req.headers["Expires"] = "0"
    req.headers['Cache-Control'] = 'public, max-age=0'
    return req
