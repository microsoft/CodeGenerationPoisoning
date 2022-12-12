import os
import secrets
from flask import render_template, url_for, flash, redirect,request,abort
from flaskblog import app, db, bcrypt
from flaskblog.models import User, Post
from flaskblog.forms import RegistrationForm, LoginForm,UpdateForm,PostForm
from flask_login import login_user,current_user,logout_user,login_required
from flaskblog import request




@app.route('/')
@app.route('/home')
def home():
    posts = Post.query.all()
    quote = request.get_quote()
    return render_template('home.htm', posts=posts,quote=quote)


@app.route('/about')
@login_required
def about():
    return render_template('about.htm')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password= bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        
        flash(
            f'You have successfully created an account for {form.username.data}! You can now log in to your account','success')
        return redirect(url_for('login'))
    return render_template('register.htm', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
         
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            
            login_user(user, remember=form.remember.data)
            return redirect(url_for('home'))
        else:
            flash('Login unsuccessful. please confirm email and password.','danger')
        
        
    return render_template('login.htm', form=form)
@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))
@app.route('/profile', methods=['GET', 'POST'])

        
def profile():
    form = UpdateForm()
    if form.validate_on_submit():
        # if form.picture.data:
        #     picture_file = save_picture(form.picture.data)
        #     current_user.image_file = picture_file
            
        current_user.username= form.username.data
        current_user.email= form.email.data
        db.session.commit()
        flash("Your account has been updated!",'success')
        return redirect(url_for('profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    
    image_file = url_for('static', filename='pics/' + current_user.image_file)
    return render_template('profile.htm', title='Profile', image_file=image_file,form=form)
     
@app.route('/post/new', methods=['GET', 'POST'])
@login_required
def new_post():
     form = PostForm()
     if form.validate_on_submit():
         post=Post(title=form.title.data,content=form.content.data, author=current_user)
         db.session.add(post)
         db.session.commit()
         
         flash("Your Post has been created",'success')
         return redirect(url_for('home'))
     return render_template('post.htm' ,form=form, legend='New Post')

@app.route('/post/<int:post_id>')
def post(post_id):
    post= Post.query.get_or_404(post_id)
    return render_template('postss.htm',post=post)

@app.route('/post/<int:post_id>/update', methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post= Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.title=form.title.data
        post.content=form.content.data
        db.session.commit()
        flash("Your post has been updated",'success')
        return redirect(url_for('post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
    return render_template('post.htm' ,form=form, legend='Update Post')
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
# @main.route('/like/<int:id>', methods=['POST', 'GET'])
# @login_required
# def upvote(id):
#     post = Post.query.get(id)
#     new_vote = Upvote(post=post, upvote=1)
#     vote_save.save()
#     return redirect(url_for('main.posts'))
  