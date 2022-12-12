from flask import render_template
from flask import redirect
from flask import flash
from flask import url_for
from flask import request
from flask_login import current_user, login_user, logout_user
from flask_login import login_required
from app import app, db
from app.forms import LoginForm, RegistrationForm
from app.forms import EditProfileForm
from app.forms import EmptyForm, PostForm
from app.forms import ResetPasswordRequestForm
from app.forms import ResetPasswordForm
from app.models import User, Post
from werkzeug.urls import url_parse
from datetime import datetime
from app.util.email import send_password_reset_email

@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@app.route('/index', methods=["GET", "POST"])
@app.route('/', methods=["GET", "POST"])
@login_required
def index():
    
    form = PostForm()

    if form.validate_on_submit():
        post = Post(body=form.post.data, author=current_user)
        db.session.add(post)
        db.session.commit()

        flash('Your post is now live!')
        return redirect(url_for('index'))

    page = request.args.get('page', 1, type=int)
    posts = current_user.followed_posts().paginate(
                page,
                app.config['POSTS_PER_PAGE'],
                False)

    next_url = url_for('index', page=posts.next_num) if posts.has_next else None
    prev_url = url_for('index', page=posts.prev_num) if posts.has_prev else None

    return render_template('index.html',
        posts=posts.items,
        form=form,
        next_url=next_url,
        prev_url=prev_url)


@app.route('/login', methods=["GET", "POST"])
def login():

    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()

    if form.validate_on_submit():

        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))

        login_user(user, remember=form.remember_me.data)

        next_page = request.args.get('next')

        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')

        return redirect(next_page)

    return render_template('login.html', title='Sign in', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = RegistrationForm()    

    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        flash('Congrats, you are a registered user now!')
        return redirect(url_for('login'))


    return render_template('register.html', title='Register', form=form)


@app.route('/user/<username>')
@login_required
def user(username):

    page = request.args.get('page', 1, type=int)
    user = User.query.filter_by(username=username).first_or_404()

    posts = user.posts.order_by(Post.timestamp.desc()).paginate(
                page,
                app.config['POSTS_PER_PAGE'],
                False
            )

    next_url = url_for('user', username=username, page=posts.next_num) \
                if posts.has_next else None
    prev_url = url_for('user', username=username, page=posts.prev_num) \
                if posts.has_prev else None

    form = EmptyForm()

    return render_template(
        'user.html',
        user=user,
        posts=posts.items,
        next_url=next_url,
        prev_url=prev_url,
        form=form)


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)

    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('edit_profile'))

    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me

    return render_template('edit_profile.html', title="Edit Profile", form=form)


@app.route('/follow/<username>', methods=["POST"])
@login_required
def follow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first()
        if user is None:
            flash('User {} not found'.format(username))
            return redirect(url_for('index'))

        if (user == current_user):
            flash('You cannot follow yourself!')
            return redirect(url_for('user', username=username))

        current_user.follow(user)

        db.session.commit()

        flash('You are now following {}!'.format(username))
        return redirect(url_for('user', username=username))

    else:

        return redirect(url_for('index'))


@app.route('/unfollow/<username>', methods=["POST"])
@login_required
def unfollow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first()
        if user is None:
            flash('User {} not found'.format(username))
            return redirect(url_for('index'))

        if (user == current_user):
            flash('You cannot unfollow yourself!')
            return redirect(url_for('user', username=username))

        current_user.unfollow(user)

        db.session.commit()

        flash('You have unfollowed {}!'.format(username))
        return redirect(url_for('user', username=username))

    else:

        return redirect(url_for('index'))


@app.route('/explore')
@login_required
def explore():

    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.timestamp.desc()).paginate(
                page,
                app.config['POSTS_PER_PAGE'],
                False)

    next_url = url_for('explore', page=posts.next_num) if posts.has_next else None
    prev_url = url_for('explore', page=posts.prev_num) if posts.has_prev else None

    return render_template('index.html',
        title='Explore',
        posts=posts.items,
        next_url=next_url,
        prev_url=prev_url)


@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        flash('Check your email for instructions to reset your password.')
        return redirect(url_for('index'))

    return render_template(
        'reset_password_request.html',
        title='Reset Password',
        form=form)


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    user = User.verify_reset_password_token(token)

    if not user:
        return redirect(url_for('index'))

    form = ResetPasswordForm()
    
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset.')
        return redirect(url_for('login'))

    return render_template('reset_password.html', form=form)
