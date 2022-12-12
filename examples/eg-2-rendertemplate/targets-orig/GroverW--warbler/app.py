import os

from flask import Flask, render_template, request, flash, redirect, session, g
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError

from forms import UserAddForm, LoginForm, MessageForm, UserEditForm
from models import db, connect_db, User, Message, Likes, Blocks

CURR_USER_KEY = "curr_user"

app = Flask(__name__)

# Get DB_URI from environ variable (useful for production/testing) or,
# if not set there, use development local db.
app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.environ.get('DATABASE_URL', 'postgres:///warbler'))

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "it's a secret")
toolbar = DebugToolbarExtension(app)

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
        return True
    
    return False


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
            db.session.add(user)
            db.session.commit()

        except IntegrityError:
            flash("Username / Email already taken", 'danger')
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

    if do_logout():
        flash('Logout Successful.', 'success')

    return redirect('/login')


##############################################################################
# General user routes:

@app.route('/users')
def list_users():
    """Page with listing of users.

    Can take a 'q' param in querystring to search by that username.
    """

    search = request.args.get('q')
    
    users_blocking = [block.user_blocking_id for block in Blocks.query.all() if block.user_being_blocked_id == g.user.id]

    if not search:
        users = User.query.filter(User.id.notin_(users_blocking)).all()
    else:
        users = (User.query.filter(
                                  User.username.like(f"%{search}%"),
                                  User.id != g.user.id,
                                  User.id.notin_(users_blocking))
                                  .all())

    return render_template('users/index.html', users=users)


@app.route('/users/<int:user_id>')
def users_show(user_id):
    """Show user profile."""
    
    user = User.query.get_or_404(user_id)

    if (user.is_blocking(g.user)):
        flash("User can't be found", "danger")
        return redirect("/")


    # snagging messages in order from the database;
    # user.messages won't be in order by default
    messages = (Message
                .query
                .filter(Message.user_id == user_id)
                .order_by(Message.timestamp.desc())
                .limit(100)
                .all())
    users_blocking = [block.user_blocking_id for block in Blocks.query.all() if block.user_being_blocked_id == g.user.id]
    likes = [message for message in user.likes if message.user_id not in users_blocking]
    return render_template('users/show.html', user=user, messages=messages, likes=likes)


@app.route('/users/<int:user_id>/following')
def show_following(user_id):
    """Show list of people this user is following."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    users_blocking = [block.user_blocking_id for block in Blocks.query.all() if block.user_being_blocked_id == g.user.id]
    likes = [message for message in user.likes if message.user_id not in users_blocking]
    return render_template('users/following.html', user=user, likes=likes)


@app.route('/users/<int:user_id>/followers')
def users_followers(user_id):
    """Show list of followers of this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    users_blocking = [block.user_blocking_id for block in Blocks.query.all() if block.user_being_blocked_id == g.user.id]
    likes = [message for message in user.likes if message.user_id not in users_blocking]
    return render_template('users/followers.html', user=user, likes=likes)


@app.route('/users/follow/<int:follow_id>', methods=['POST'])
def add_follow(follow_id):
    """Add a follow for the currently-logged-in user."""
    followed_user = User.query.get_or_404(follow_id)
    if not g.user or g.user.id == follow_id or followed_user.is_blocking(g.user):
        flash("Access unauthorized.", "danger")
        return redirect("/")

    g.user.following.append(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/stop-following/<int:follow_id>', methods=['POST'])
def stop_following(follow_id):
    """Have currently-logged-in-user stop following this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_user = User.query.get_or_404(follow_id)
    g.user.following.remove(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/<int:user_id>/blocked-users')
def block_user(user_id):
    """ Block/unblock users from following/commenting/liking another user's posts"""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    users_blocking = [block.user_blocking_id for block in Blocks.query.all() if block.user_being_blocked_id == g.user.id]
    likes = [message for message in user.likes if message.user_id not in users_blocking]
    return render_template('users/blocked-users.html', user=user, likes=likes)


@app.route('/users/block/<int:block_id>', methods=['POST'])
def add_block(block_id):
    """Add a follow for the currently-logged-in user."""
    if not g.user or g.user.id == block_id:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    blocked_user = User.query.get_or_404(block_id)
    g.user.blocked_users.append(blocked_user)

    if g.user.is_following(blocked_user):
        g.user.following.remove(blocked_user)
    
    if blocked_user.is_following(g.user):
        blocked_user.following.remove(g.user)


    db.session.commit()

    return redirect(f"/users/{g.user.id}/blocked-users")


@app.route('/users/unblock/<int:block_id>', methods=['POST'])
def stop_blocking(block_id):
    """Have currently-logged-in-user stop blocking this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    blocked_user = User.query.get_or_404(block_id)
    g.user.blocked_users.remove(blocked_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/blocked-users")


@app.route('/users/profile', methods=["GET", "POST"])
def profile():
    """Update profile for current user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = UserEditForm(obj=g.user)

    if form.validate_on_submit():
        if not User.authenticate(g.user.username, form.data["password"]):
            flash("Invalid password.", "danger")
            return render_template('/users/edit.html', form=form)  
        # data = {k:v for k,v in form.data.items() if k != "csrf_token"}
        # data["image_url"] = data["image_url"] or None
        # data["header_image_url"] = data["header_image_url"] or None

        g.user.username = form.data["username"]
        g.user.email = form.data["email"]
        g.user.image_url = form.data["image_url"] or None
        g.user.header_image_url = form.data["header_image_url"] or None
        g.user.bio = form.data["bio"]

        db.session.commit()

        flash("Profile edited!", "success")
        return redirect(f'/users/{g.user.id}')

    return render_template('/users/edit.html', form=form) 


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

@app.route('/messages/new', methods=["GET", "POST"])
def messages_add():
    """Add a message:

    Show form if GET. If valid, update message and redirect to user page.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = MessageForm()

    if form.validate_on_submit():
        msg = Message(text=form.text.data)
        g.user.messages.append(msg)
        db.session.commit()

        return redirect(f"/users/{g.user.id}")

    return render_template('messages/new.html', form=form)


@app.route('/messages/<int:message_id>', methods=["GET"])
def messages_show(message_id):
    """Show a message."""

    msg = Message.query.get(message_id)
    user = User.query.get_or_404(msg.user_id)
    
    if (user.is_blocking(g.user)):
        flash("Message can't be found", "danger")
        return redirect("/")


    return render_template('messages/show.html', message=msg)


@app.route('/messages/<int:message_id>/delete', methods=["POST"])
def messages_destroy(message_id):
    """Delete a message."""
    message =  Message.query.get_or_404(message_id)
    if not g.user or g.user.id != message.user_id:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    msg = Message.query.get(message_id)
    db.session.delete(msg)
    db.session.commit()

    return redirect(f"/users/{g.user.id}")


@app.route('/likes/<int:msg_id>/update', methods=["POST"])
def likes_add(msg_id):
    message =  Message.query.get_or_404(msg_id)
    if not g.user or g.user.id == message.user_id:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    existing_like = Likes.query.filter(
                                    Likes.user_id == g.user.id,
                                    Likes.message_id == msg_id).first()

    if existing_like:
        db.session.delete(existing_like)
    else:
        like = Likes(user_id=g.user.id, message_id=msg_id)
        db.session.add(like)
    
    db.session.commit()

    return redirect("/")


@app.route('/users/<int:user_id>/likes')
def users_likes(user_id):
    """Show list of likes for this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    users_blocking = [block.user_blocking_id for block in Blocks.query.all() if block.user_being_blocked_id == g.user.id]
    # likes = Message.query.filter(Message.user_id.notin_(users_blocking)).all()
    user = User.query.get_or_404(user_id)
    likes = [message for message in user.likes if message.user_id not in users_blocking]
    return render_template('users/likes.html', user=user, likes=likes)


##############################################################################
# Homepage and error pages


@app.route('/')
def homepage():
    """Show homepage:

    - anon users: no messages
    - logged in: 100 most recent messages of followed_users
    """

    if g.user:
        users_blocking = [block.user_blocking_id for block in Blocks.query.all() if block.user_being_blocked_id == g.user.id]

        following_user_ids = [user.id for user in g.user.following] 
        following_user_ids.append(g.user.id)
        messages = (Message
                    .query
                    .filter(Message.user_id.in_(following_user_ids),
                            Message.user_id.notin_(users_blocking))
                    .order_by(Message.timestamp.desc())
                    .limit(100)
                    .all())
        liked_messages = [message.id for message in g.user.likes]
        return render_template('home.html', messages=messages, liked_messages=liked_messages)

    else:
        return render_template('home-anon.html')


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
