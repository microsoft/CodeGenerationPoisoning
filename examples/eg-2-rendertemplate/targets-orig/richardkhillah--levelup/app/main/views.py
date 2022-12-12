from flask import render_template, session, redirect, url_for, flash
from flask import request, make_response
from flask_login import login_required, current_user
from flask_sqlalchemy import get_debug_queries
from flask import current_app, abort
from .forms import EditProfileForm, EditProfileAdminForm
from .forms import NewTownForm, EditTownForm
from ..blog.forms import PostForm

from datetime import datetime

from . import main
from .. import db
from ..models.models import User, Role, Permission, Town
from ..models.blog import Post
from ..models.township import Source, Item, Unlock
from ..email import send_email
from ..decorators import admin_required, permission_required

@main.after_app_request
def after_request(response):
    for query in get_debug_queries():
        if query.duration >= current_app.config['LEVELUP_SLOW_DB_QUERY_TIME']:
            current_app.logger.warning(
                'Slow query: %s\nParameters: %s\nDuration: %fs\nContext: %s\n'
                % (query.statement, query.parameters, query.duration,
                   query.context))
    return response

@main.route('/shutdown')
def server_shutdown():
    if not current_app.testing:
        abort(404)
    shutdown = request.environ.get('werkzeug.server.shutdown')
    if not shutdown:
        abort(500)
    shutdown()
    return 'Shutting down...'

@main.route('/')
def index():
    unlock = Unlock()
    if current_user.is_authenticated and current_user.town:
        unlock.level = current_user.town.level + 1
        unlock.sources = Source.query.filter_by(required_level=unlock.level).all()
        unlock.items = Item.query.filter_by(required_level=unlock.level).all()
    else:
        unlock = None



    return render_template('index.html', unlock=unlock)

@main.route('/user/<username>')
def user(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        abort(404)
    posts = user.posts.order_by(Post.timestamp.desc()).all()
    return render_template('user.html', user=user, posts=posts)

@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user)
        db.session.commit()
        flash('Your profile has been updated.')
        return redirect(url_for('main.user', username=current_user.username))
    form.name.data =  current_user.name
    form.location.data =  current_user.location
    form.about_me.data =  current_user.about_me
    return render_template('edit_profile.html', form=form)

@main.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.role = Role.query.get(form.role.data)
        user.confirmed = form.confirmed.data
        user.name = form.name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        db.session.add(user)
        db.session.commit()
        flash('User profile has been updated')
        return redirect(url_for('.user', username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.role.data = user.role
    form.confirmed.data = user.confirmed
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template('edit_profile.html', form=form, user=user)

@main.route('/follow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def follow(username):
    """
    This view function loads the requested user,
    verifies that it is valid and
    that it isn’t already followed by the logged-in user,
    and then calls the follow() helper function in the User
    model to establish the link.
    """
    # Load the requested user,
    user = User.query.filter_by(username=username).first()

    # verify that the user is valid
    if user is None:
        flash("Invalid user")
        return redirect(url_for('.index'))

    # and that it isn’t already followed by the logged-in user,
    if user.is_followed_by(current_user):
        flash("You already follow this user.")
        return redirect(url_for('.user', username=username))

    # Call the follow() helper function in the User model
    current_user.follow(user)
    flash("You now follow %s" % username)
    return redirect(url_for('.user', username=username))

@main.route('/unfollow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def unfollow(username):
    """This view function is implemented similar to /follow/<username>."""
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash("Invalid user")
        return redirect(url_for('.index'))
    if not current_user.is_following(user):
        flash("You do not follow this user.")
        return redirect(url_for('.user', username=username))
    current_user.unfollow(user)
    flash("You stopped following %s" % username)
    return redirect(url_for('.user', username=username))

@main.route('/followers/<username>')
def followers(username):
    """
    This function loads and validates the requested user,
    then paginates its followers relationship. Because the query for
    followers returns Follow instances, the list is converted into another
    list that has user and timestamp fields in each entry so that
    rendering is simpler.
    """
    # Load the requested user
    user = User.query.filter_by(username=username).first()

    # validate requested user
    if user is None:
        flash("Invalid user.")
        return redirect(url_for('.index'))

    # paginate requested user followers
    page = request.args.get('page', 1, type=int)
    pagination = user.followers.paginate(
        page, per_page=int(current_app.config['LEVELUP_POSTS_PER_PAGE']),
        error_out=False)

    # Convert follwers instance list into a list containing dicts of
    # {following user, timestamp}
    follows = [ {'user': item.follower, 'timestamp': item.timestamp}
                    for item in pagination.items]
    return render_template('followers.html', title="Followers of ",
                endpoint='.followers', pagination=pagination,
                user=user, follows=follows)

@main.route('/followed-by/<username>')
def followed_by(username):
    """This view function is implemented similar to /followers/<username>"""
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash("Invalid User")
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followed.paginate(
        page, per_page=int(current_app.config['LEVELUP_POSTS_PER_PAGE']),
        error_out=False)
    follows = [{'user': item.followed, 'timestamp': item.timestamp}
                    for item in pagination.items]
    return render_template('followers.html', title="Followers of ",
                endpoint='.followers', pagination=pagination,
                user=user, follows=follows)

@main.route('/register-town', methods=['GET', 'POST'])
@login_required
def register_town():
    # if user has town already, redirect to .landing
    if current_user.town is not None:
        return redirect(url_for('.index'))

    form = NewTownForm()
    if form.validate_on_submit():
        town = Town(name=form.town_name.data,
                    level=form.level.data,
                    population=form.population.data,
                    population_cap=form.population_cap.data,
                    coins=form.coins.data,
                    township_cash=form.township_cash.data)
        town.owner = current_user
        db.session.add(town)
        db.session.commit()

        flash('Form Submitted')
        return redirect(url_for('.index'))
    return render_template('register_town.html', form=form)

@main.route('/edit-town/', methods=['GET', 'POST'])
@login_required
def edit_town():
    town = Town.query.get_or_404(current_user.town.id)
    form = EditTownForm()
    if form.validate_on_submit():
        town.name = form.town_name.data
        town.level = form.level.data
        town.population = form.population.data
        town.population_cap = form.population_cap.data
        town.coins = form.coins.data
        town.township_cash = form.township_cash.data
        db.session.add(town)
        db.session.commit()
        flash("Success! Your town has been updated.")
        return redirect(url_for('.index'))
    form.town_name.data = town.name
    form.level.data = town.level
    form.population.data = town.population
    form.population_cap.data = town.population_cap
    form.coins.data = town.coins
    form.township_cash.data = town.township_cash
    return render_template('edit_town.html', form=form)
