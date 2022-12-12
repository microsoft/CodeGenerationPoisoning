import os

from flask import Flask, render_template, request, flash, redirect, session, g, url_for
# from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError

from forms import UserAddForm, LoginForm, MessageForm, EditProfileForm, ChangePasswordForm
from models import db, connect_db, User, Message, Likes, Follows

CURR_USER_KEY = "curr_user"

app = Flask(__name__, static_url_path='/static')

# Get DB_URI from environ variable (useful for production/testing) or,
# if not set there, use development local db.
app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.environ.get('DATABASE_URL', 'postgres:///warbler'))

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
# app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "it's a secret")
# toolbar = DebugToolbarExtension(app)

connect_db(app)



    
        
##############################################################################
# User signup/login/logout


@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])

    else:
        g.user = None


def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Logout user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]
    
def authorize(f):
    def unauth():
        flash("Access unauthorized.", "danger")
        return render_template("home-anon.html")
    def wrapper(*args, **kwargs):
        f(*args, **kwargs)
    if g:
        return wrapper
    else:
        return unauth
        
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
        user = User.authenticate(form.username.data,
                                 form.password.data)

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", 'danger')

    return render_template('users/login.html', form=form)


@app.route('/logout')
def logout():
    """Handle logout of user."""
    do_logout()
    return redirect(url_for("login"))


##############################################################################
# General user routes:


@authorize
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

@authorize
@app.route('/users/<int:user_id>')
def users_show(user_id):
    """Show user profile."""

    user = User.query.get_or_404(user_id)
    messages = Message.get_filtered_messages([user_id])
    return render_template('users/show.html', user=user, messages=messages)

@authorize
@app.route('/users/<int:user_id>/following')
def show_following(user_id):
    """Show list of people this user is following."""

    user = User.query.get_or_404(user_id)
     
    return render_template('users/associates.html', user=user, associates=user.following)

@authorize
@app.route('/users/<int:user_id>/followers')
def users_followers(user_id):
    """Show list of followers of this user."""

    user = User.query.get_or_404(user_id)
    return render_template('users/associates.html', user=user, associates=user.followers)

@authorize
@app.route('/users/follow/<int:follow_id>', methods=['POST'])
def add_follow(follow_id):
    """Add a user to the following relationship for the currently-logged-in user."""

    followed_user = User.query.get_or_404(follow_id)
    g.user.following.append(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")

@authorize
@app.route('/users/stop-following/<int:follow_id>', methods=['POST'])
def stop_following(follow_id):
    """Have currently-logged-in-user stop following this user."""

    followed_user = User.query.get(follow_id)
    g.user.following.remove(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")

@authorize
@app.route("/users/<int:user_id>/likes", methods=["GET"])
def show_likes_page(user_id):
    """Show user likes page"""
    liked = [x.id for x in g.user.likes if x.user_id != g.user.id]
    messages = Message.get_liked_messages(liked)
    likes = [x.id for x in g.user.likes if x.id != g.user.id]
    return render_template('users/likes.html', user=g.user, messages=messages, likes=likes)

@authorize
@app.route('/users/profile', methods=["GET", "POST"])
def update_profile():
    """Update profile for current user."""
    form = EditProfileForm()    
    
    if form.validate_on_submit():
        try:
            user = User.authenticate(
                username=g.user.username,
                password=form.password.data                
            )
            if user:
                User.update_user(user.id, form.email.data, form.image_url.data, form.header_image_url.data, form.bio.data, form.location.data)
                db.session.commit()
            else:
                flash("Error, please recheck your info", 'danger')
        except IntegrityError:
            flash("Error, please recheck your info", 'danger')
            return render_template('users/edit.html', form=form)

        return redirect("/")

    else:
        return render_template('users/edit.html', form=form)

@authorize
@app.route('/users/changepw', methods=["GET", "POST"])
def changepw():
    """Update profile for current user."""
    form = ChangePasswordForm()  
    if form.validate_on_submit():
        try:
            user = User.authenticate(
                username=g.user.username,
                password=form.oldPassword.data                
            )
            if user:
                User.change_password(g.user.id, form.newPassword1.data)
                db.session.commit()
            else:
                flash("Error, please recheck your info", 'danger')
        except IntegrityError:
            flash("Error, please recheck your info", 'danger')
            return render_template('users/edit.html', form=form)

        return redirect("/")
    else:
        return render_template('users/change-password.html', form=form)       
    
@authorize
@app.route('/users/delete', methods=["POST"])
def delete_user():
    """Delete user."""

    do_logout()

    db.session.delete(g.user)
    db.session.commit()

    return redirect("/signup")


##############################################################################
# Messages routes:

@authorize
@app.route('/messages/new', methods=["GET", "POST"])
def messages_add():
    """Add a message:

    Show form if GET. If valid, update message and redirect to user page.
    """
    form = MessageForm()
    if form.validate_on_submit():
        message = Message(text=form.text.data)
        g.user.messages.append(message)
        db.session.commit()

        return redirect(f"/users/{g.user.id}")

    return render_template('messages/new.html', form=form)

@authorize
@app.route('/messages/<int:message_id>', methods=["GET"])
def messages_show(message_id):
    """Show a message."""    
    message = Message.get_message_by_id(message_id)
    return render_template('messages/show.html', message=message)

@authorize
@app.route('/messages/<int:message_id>/delete', methods=["POST"])
def messages_destroy(message_id):
    """Delete a message."""
   
    Message.delete_message(message_id)
    db.session.commit()

    return redirect(f"/users/{g.user.id}")

@authorize
@app.route("/do_like", methods=["POST"])
def do_like():
    """Handle likes from javascript"""    
    message_id = request.form["message_id"]    
    if int(message_id) in [x.id for x in g.user.likes]:        
        Likes.delete_like(g.user.id, message_id)
    else:
        Likes.add_like(g.user.id, message_id)        
    db.session.commit()
    return 'None'
        
##############################################################################
# Homepage and error pages


@app.route('/')
def homepage():
    """Show homepage:    
    The homepage for logged-in-users should show the last 100 warbles only from the users that the logged-in user is following, and that user, rather than warbles from all users.
    """
    if g.user:
        messages = Message.get_filtered_messages([y.id for y in g.user.following])        
        likes = [x.id for x in g.user.likes if x.id != g.user.id]
        return render_template('home.html', messages=messages, likes=likes)
    else:
        return render_template("home-anon.html")

@app.errorhandler(404)
def page_not_found(error):
    return render_template("messages/page404.html", title = '404'), 404

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



        