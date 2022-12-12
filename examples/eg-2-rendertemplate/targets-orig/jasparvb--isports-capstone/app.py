"""Flask app for iSports"""

from flask import Flask, request, redirect, render_template, flash, jsonify, session, g, send_from_directory
from sqlalchemy.exc import IntegrityError
from flask_debugtoolbar import DebugToolbarExtension
from models import db, connect_db, User, Favorite, Follow
from forms import AddUserForm, EditUserForm, LoginUserForm, AddFollow
from isports import Isports
import os

CURR_USER_KEY = "curr_user"
LANGUAGE_KEY = "language"

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://postgres:41361@localhost/isports')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'mylittlesecret')
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False

connect_db(app)
debug = DebugToolbarExtension(app)
isports = Isports()

@app.route("/")
def home():
    """Render homepage with top sports news headlines"""
    articles = isports.get_top_news(session[LANGUAGE_KEY])
    return render_template("home.html", articles=articles)


@app.route('/language', methods=['POST'])
def set_language():
    """Sets the preferred language in the session"""

    language = request.json['language']
    session[LANGUAGE_KEY] = language
    
    return (jsonify(status={"language":language}), 201)
    

@app.route('/favicon.ico')
def favicon():
    """Set the path to the favicon"""
    return send_from_directory(os.path.join(app.root_path, 'static', 'img'), 'favicon.ico', mimetype='image/png')


############################################################################################
# Signup/Login/Logout
############################################################################################

@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global.
    Save array of languages to g and set current language from session"""

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])

    else:
        g.user = None

    g.lang = isports.languages

    if LANGUAGE_KEY in session:
        g.selected_lang = session[LANGUAGE_KEY]
    else:
        session[LANGUAGE_KEY] = "en"
        g.selected_lang = "en"


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

    form = AddUserForm()

    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
            )
            db.session.commit()

        except IntegrityError:
            flash("Username already taken", 'danger')
            return render_template('signup.html', form=form)

        do_login(user)
        flash("Welcome to iSports! Start adding items to follow below.", 'success')
        return redirect(f"/user")

    else:
        return render_template('signup.html', form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login."""

    form = LoginUserForm()

    if form.validate_on_submit():
        user = User.login(form.username.data,
                                 form.password.data)

        if user:
            do_login(user)
            flash(f"Hello, {user.username}, welcome back!", "success")
            return redirect(f"/news")

        flash("Invalid credentials.", 'danger')

    return render_template('login.html', form=form)


@app.route('/logout')
def logout():
    """Handle logout of user."""

    do_logout()
    flash("You have logged out", 'success')
    return redirect("/login")


############################################################################################
# User Profile
############################################################################################

@app.route('/user')
def show_user():
    """Show user profile."""

    if not g.user:
        flash("You must log in to access that page.", "danger")
        return redirect("/login")

    form = AddFollow()
    return render_template('user.html', form=form)


@app.route('/user/edit', methods=['GET','POST'])
def edit_user():
    """Edit user profile."""

    if not g.user:
        flash("You must log in to access that page.", "danger")
        return redirect("/login")

    form = EditUserForm(obj=g.user)

    if form.validate_on_submit():
        try:
            g.user.username = form.username.data
            g.user.email = form.email.data

            db.session.commit()

            flash("User profile updated", 'success')
            return redirect(f"/user")

        except IntegrityError:
            flash("Username already taken", 'danger')
            return render_template('edit-user.html', form=form)
    else:
        return render_template('edit-user.html', form=form)


@app.route('/user/delete', methods=['POST'])
def delete_user():
    """Delete user profile."""

    if not g.user:
        flash("You must log in to access that page.", "danger")
        return redirect("/login")

    db.session.delete(g.user)
    db.session.commit()

    return redirect("/")


############################################################################################
# Follow
############################################################################################

@app.route('/follow', methods=['POST'])
def add_follow():
    """Add an item to follow"""

    if not g.user:
        flash("You must log in to access that page.", "danger")
        return redirect("/login")

    form = AddFollow()

    if form.validate_on_submit():
        name = form.name.data
        category = form.category.data
        sportsdb_id = form.sportsdb_id.data
        tb_image = form.tb_image.data if form.tb_image.data else "/static/img/isports-default.png"

        if category == "league":
            tb_image = isports.get_league_image(sportsdb_id)

        follow = Follow(name=name, category=category, user_id=g.user.id, sportsdb_id=sportsdb_id, tb_image=tb_image)
        db.session.add(follow)
        db.session.commit()
    else:
        flash("Invalid input! Select an item from the list.", "danger")
    return redirect(f"/user")


@app.route("/follow/<follow_id>/delete", methods=['POST'])
def delete_follow(follow_id):
    """Delete follow"""
    if not g.user:
        flash("You must log in to access that page.", "danger")
        return redirect("/login")
    
    follow = Follow.query.get_or_404(follow_id)

    db.session.delete(follow)
    db.session.commit()

    return redirect(f"/user")


############################################################################################
# News
############################################################################################

@app.route("/search")
def search_news():
    """Search sports news"""
    
    search = request.args["q"]
    articles = isports.get_all_news(search, session[LANGUAGE_KEY])

    return render_template('search.html', articles=articles, search=search)

    
@app.route('/news')
def my_news():
    """Displays news articles from the items the user follows"""

    if not g.user:
        flash("You must log in to access that page.", "danger")
        return redirect("/login")
    articles = {val.name: isports.get_my_news(val.name, session[LANGUAGE_KEY]) for val in g.user.follows}
    
    return render_template('news.html', articles=articles)


@app.route('/news', methods=['POST'])
def load_more_news():
    """Retrieves the next page of articles for the term"""

    term = request.json['term']
    page = request.json['page']
    articles = isports.get_my_news(term, session[LANGUAGE_KEY], page)
    
    return (jsonify(articles=articles), 201)


############################################################################################
# Events
############################################################################################

@app.route('/events')
def my_events():
    """Displays upcoming and past events from leagues and teams the user follows"""

    if not g.user:
        flash("You must log in to access that page.", "danger")
        return redirect("/login")

    events = {val.name: isports.get_my_events(val.sportsdb_id, val.category) for val in g.user.follows if val.category == "league" or val.category == "team"}
    past_events = {val.name: isports.get_my_past_events(val.sportsdb_id, val.category) for val in g.user.follows if val.category == "league" or val.category == "team"}
    
    return render_template('events.html', events=events, past_events=past_events)


############################################################################################
# Favorites
############################################################################################

@app.route("/favorites")
def get_favorites():
    """Saved sports news articles"""

    if not g.user:
        flash("You must log in to access that page.", "danger")
        return redirect("/login")
        
    return render_template('favorites.html')


@app.route("/favorites", methods=['POST'])
def add_favorite():
    """Save a sports news article"""

    if not g.user:
        flash("You must log in to access that page.", "danger")
        return redirect("/login")
    
    title = request.json['title']
    url = request.json['url']
    image_url = request.json['image_url']
    published_at = request.json['published_at']

    favorite = Favorite(title=title, url=url, image_url=image_url, published_at=published_at, user_id=g.user.id)

    db.session.add(favorite)
    db.session.commit()

    return (jsonify(favorite={"id": favorite.id}), 201)


@app.route("/favorites/<int:id>", methods=['DELETE'])
def delete_favorite(id):
    """Delete a saved article"""

    if not g.user:
        flash("You must log in to access that page.", "danger")
        return redirect("/login")

    article = Favorite.query.get_or_404(id)
    db.session.delete(article)
    db.session.commit()

    return jsonify(message="Deleted")