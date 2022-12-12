from flask import render_template, url_for, flash, redirect, request, abort
from bank import app, db, bcrypt
from bank.forms import RegistrationForm, LoginForm, UpdateAccountForm, PostForm, EditProfileForm, DonateForm
from bank.models import User, Post, Donate
from flask_login import login_user, current_user, logout_user, login_required
from datetime import datetime
from flask_sqlalchemy import *
import os
import errno
import secrets
from PIL import Image


def make_sure_path_exists(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    f_name, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    path = os.path.join(app.root_path, 'static/images/' + current_user.username)
    make_sure_path_exists(path)
    picture_path = os.path.join(app.root_path, path, picture_fn)
    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)
    return os.path.join(current_user.username, picture_fn)


@app.route("/")
@app.route("/home")
def home():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(page=page, per_page=5)
    donates = Donate.query.order_by(Donate.date_posted.desc()).paginate(page=page, per_page=5)

    my_list = Donate.query.all()
    total_blood = 0
    o_neg = 0
    o_pos = 0
    a_neg = 0
    a_pos = 0
    b_neg = 0
    b_pos = 0
    ab_neg = 0
    ab_pos = 0
    for q in my_list:
        total_blood += q.quantity
        if q.name_blood == 'O-':
            o_neg += q.quantity
        if q.name_blood == 'O+':
            o_pos += q.quantity
        if q.name_blood == 'A-':
            a_neg += q.quantity
        if q.name_blood == 'A+':
            a_pos += q.quantity
        if q.name_blood == 'B-':
            b_neg += q.quantity
        if q.name_blood == 'B+':
            b_pos += q.quantity
        if q.name_blood == 'AB-':
            ab_neg += q.quantity
        if q.name_blood == 'AB+':
            ab_pos += q.quantity
    return render_template('home.html', posts=posts, donates=donates, total_blood=total_blood, o_neg=o_neg, o_pos=o_pos,
                           a_neg=a_neg, a_pos=a_pos, b_neg=b_neg, b_pos=b_pos, ab_neg=ab_neg, ab_pos=ab_pos)


@app.route("/about")
def about():
    # user = User.query.filter_by(username=username).first_or_404()
    image_file = url_for('static', filename='images/' + current_user.image_file)
    return render_template('about.html', title='About', image_file=image_file)


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password,
                    phone=form.phone.data, post_index=form.post_index.data, address=form.address.data,
                    city=form.city.data, blood_group=form.blood_group.data)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login unsuccessful. Please check username and password', 'danger')
    return render_template('login.html', title='Login', form=form)


@app.route("/logout")
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('home'))


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.about = form.about.data
        current_user.phone = form.phone.data
        current_user.post_index = form.post_index.data
        current_user.address = form.address.data
        current_user.city = form.city.data
        current_user.blood_group = form.blood_group.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.about.data = current_user.about
        form.phone.data = current_user.phone
        form.post_index.data = current_user.post_index
        form.address.data = current_user.address
        form.city.data = current_user.city
        form.blood_group.data = current_user.blood_group
    image_file = url_for('static', filename='images/' + current_user.image_file)
    return render_template('account.html', title='Account', image_file=image_file, form=form)


@app.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    posts = Post.query.filter_by(user_id=user.id).paginate(page, 10, False)
    return render_template('user.html', user=user, posts=posts.items)


@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last__seen = datetime.utcnow()
        db.session.commit()


@app.route("/donate/new", methods=['GET', 'POST'])
@login_required
def new_donate():
    form = DonateForm()
    if form.validate_on_submit():
        donate = Donate(name_blood=form.name_blood.data, quantity=form.quantity.data, author=current_user)
        db.session.add(donate)
        db.session.commit()
        flash('Your donate has been created!', 'success')
        return redirect(url_for('home'))
    return render_template('create_donate.html', title='New Donate', form=form, legend='New Donate')


@app.route("/post/new", methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect(url_for('home'))
    return render_template('create_post.html', title='New Post', form=form, legend='New Post')


@app.route("/post/<int:post_id>")
def post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', title=post.title, post=post)


@app.route("/donate/<int:donate_id>")
def donate(donate_id):
    donate = Donate.query.get_or_404(donate_id)
    return render_template('donate.html', name_blood=donate.name_blood, donate=donate)


@app.route("/post/<int:post_id>/update", methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect(url_for('post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
    return render_template('create_post.html', title='Update Post', form=form, legend='Update Post')


@app.route("/donate/<int:donate_id>/update", methods=['GET', 'POST'])
@login_required
def update_donate(donate_id):
    donate = Donate.query.get_or_404(donate_id)
    if donate.author != current_user:
        abort(403)
    form = DonateForm()
    if form.validate_on_submit():
        donate.name_blood = form.name_blood.data
        donate.quantity = form.quantity.data
        db.session.commit()
        flash('Your donate has been updated!', 'success')
        return redirect(url_for('donate', donate_id=donate.id))
    elif request.method == 'GET':
        form.name_blood.data = donate.name_blood
        form.quantity.data = donate.quantity
    return render_template('create_donate.html', title='Update Donate', form=form, legend='Update Donate')


@app.route("/post/<int:post_id>/delete", methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')
    return redirect(url_for('home'))


@app.route("/donate/<int:donate_id>/delete", methods=['POST'])
@login_required
def delete_donate(donate_id):
    donate = Donate.query.get_or_404(donate_id)
    if donate.author != current_user:
        abort(403)
    db.session.delete(donate)
    db.session.commit()
    flash('Your donate has been deleted!', 'success')
    return redirect(url_for('home'))


@app.route('/follow/<username>')
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not found.'.format(username))
        return redirect(url_for('index'))
    if user == current_user:
        flash('You cannot follow yourself!')
        return redirect(url_for('user', username=username))
    current_user.follow(user)
    db.session.commit()
    flash('You are following {}!'.format(username))
    return redirect(url_for('user', username=username))


@app.route('/unfollow/<username>')
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not found.'.format(username))
        return redirect(url_for('index'))
    if user == current_user:
        flash('You cannot unfollow yourself!')
        return redirect(url_for('user', username=username))
    current_user.unfollow(user)
    db.session.commit()
    flash('You are not following {}.'.format(username))
    return redirect(url_for('user', username=username))


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about = form.about.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about.data = current_user.about
        return render_template('edit_profile.html', title='Edit Profile', form=form)
