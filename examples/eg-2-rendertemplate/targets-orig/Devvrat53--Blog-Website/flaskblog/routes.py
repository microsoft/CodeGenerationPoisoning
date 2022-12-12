from flask import render_template, url_for, flash, redirect, request
from flaskblog import app, db, bcrypt
from flaskblog.forms import RegistrationForm, LoginForm
from flaskblog.models import User, Post
from flask_login import login_user, current_user, logout_user, login_required

posts = [
    {
        'author': 'Devvrat Mungekar',
        'title': 'Blog Post 1',
        'content': 'First post content',
        'date_posted': 'April 24, 2020'
    },
    {
        'author': 'Himani Joshi',
        'title': 'Blog Post 2',
        'content': 'Second post content',
        'date_posted': 'April 23, 2020'
    }
]

@app.route("/")
@app.route("/home")
def home():
    #return "<h1>Home Page</h1>"
    return render_template('home.html', posts= posts)

@app.route("/about")
def about():
    #return "<h1>About Page</h1>"
    return render_template('about.html', title='About')

@app.route("/register", methods= ['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password= bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user= User(username= form.username.data, email= form.email.data, password= hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You will now be able to log in', 'success')
        return redirect(url_for('login')) # 'home is the name of the function which is present in the same file'
    return render_template('register.html', title= 'Register', form= form)

@app.route("/login", methods= ['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email= form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember= form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title= 'Login', form= form)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route("/account")
@login_required
def account():
    return render_template('account.html', title= 'Account')

