from flask import render_template, redirect, request, url_for, flash
from web_app import app, db, bcrypt, date_now
from web_app.forms import SubForm, RegForm, LogForm, UpdateForm, CalcForm, PostForm, TodoForm, RatesForm, ValidationError
from web_app.models import Subscribers, Users, Post, Todo
from flask_login import login_user, current_user, logout_user, login_required
import secrets
import os
from PIL import Image
import requests


@app.route("/calculator/interest", methods=["GET", "POST"])
def calc():
    form = CalcForm()
    print(form.interest.data)
    if form.validate_on_submit():
        print(form.interest.data)
        result = form.balance.data * (1 + form.interest.data) ** form.years.data
        round_result = round(result, 2)
        return render_template("interest.html", form=form, round_result=round_result, date_now=date_now, title="Interest Calculator")
    return render_template('interest.html', form=form, date_now=date_now, title='Interests Calculator')


@app.route("/rates", methods=["GET", "POST"])
def exchange():
    form = RatesForm()
    if form.validate_on_submit():
        form.rate.data = form.rate.data.upper()  # make input form uppercase
        form.base.data = form.base.data.upper()
        param = {"base=": form.base.data, "symbols=": form.rate.data}  # apply form input to query param
        r = requests.get(url="https://api.exchangeratesapi.io/latest?", params=param, timeout=4)
        data = r.json()
        currency = data.get('rates', {}).get(form.rate.data)  # currency = data['rates'][form.rate.data]
        value = form.rate.data  # requested value (e.g. NOK)
        dt = data['date']
        base = data['base']
        if currency is not None:
            return render_template("rates.html", date_now=date_now, title="Exchange Rates",
                                   currency=currency, value=value, dt=dt, base=base, form=form)
        if currency is None:
            flash(f'"{form.rate.data}" Is not a valid currency!', 'danger')
            return redirect(url_for('exchange'))
    return render_template("rates.html", date_now=date_now, title="Exchange Rates", form=form)


@app.route("/")
@app.route("/home")
def home():
    return render_template("home.html", date_now=date_now, title="Home")


@app.route("/posts/")
def all_posts():
    posts = Post.query.order_by(Post.date_posted)
    return render_template("posts.html", date_now=date_now, posts=posts, title="Posts")


@app.route("/todo/all")
@login_required
def todo_all():
    if current_user.is_authenticated:
        todos = Todo.query.all()
        return render_template("all_todos.html", todos=todos, date_now=date_now, title="My Todo's")


@app.route("/todo/", methods=["GET", "POST"])
@login_required
def todo_func():
    form = TodoForm()
    if form.validate_on_submit():
        todo = Todo(comment=form.comment.data, priority=form.priority.data,
                    mail=current_user)  # takes comment and prio + users email
        db.session.add(todo)
        db.session.commit()
        flash("Todo created!", "success")
        return redirect(url_for('todo_func'))
    return render_template("todo.html", date_now=date_now, title="Todo", form=form)


@app.route("/post/new", methods=["GET", "POST"])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Post created!', 'success')
        return redirect(url_for('all_posts'))
    return render_template("create_post.html", title="New Post", date_now=date_now, form=form)


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        flash(f"You are already logged in {current_user.mail}", "success")
        return redirect(url_for("home"))
    form = RegForm()
    if form.validate_on_submit():
        pass_hash = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = Users(username=form.username.data, mail=form.mail.data, password=pass_hash)
        db.session.add(user)
        db.session.commit()
        flash(f"Thanks for signing up {form.username.data}! You are now logged in!", "success")
        return redirect(url_for("login"))
    return render_template("register.html", title="Register", date_now=date_now, form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))
    form = LogForm()
    if form.validate_on_submit():
        user = Users.query.filter_by(mail=form.mail.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for("home"))
        else:
            flash("Login unsuccessful!", "danger")
    return render_template("login.html", title="Login", date_now=date_now, form=form)


@app.route("/subscribe", methods=["GET", "POST"])
def subscribe():
    if current_user.is_authenticated:
        flash(f"You have already registered an account and will receive notifications!", "success")
        return redirect(url_for("home"))
    form = SubForm()
    if form.validate_on_submit():
        user = Subscribers(email=form.email.data)
        db.session.add(user)
        db.session.commit()
        flash(f"Thank you for subscribing {form.email.data} !", "success")
        return redirect(url_for("home"))
    else:

        return render_template("subscribe.html", title="subscribe", date_now=date_now, form=form)


@app.route("/logout")
@login_required
def logout():
    if current_user.is_authenticated:
        logout_user()
        flash(f"Successfully logged out!", "danger")
        return redirect(url_for("home"))


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.split(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/images', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = UpdateForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.mail = form.mail.data
        db.session.commit()
        flash(f"Profile was successfully updated!", "success")
        return redirect(url_for("profile"))
    elif request.method == "GET":
        form.username.data = current_user.username
        form.mail.data = current_user.mail
    image_file = url_for('static', filename='images/' + current_user.image_file)
    return render_template("profile.html", title="Profile", image_file=image_file, form=form, date_now=date_now)


@app.route("/success")
def success():
    return render_template("success.html", title="Success", date_now=date_now)


@app.route("/about")
def about():
    return render_template("about.html", title="About", date_now=date_now)


@app.route("/forum")
def forum():
    return render_template("forum.html", title="forum", date_now=date_now, method=["POST", "GET"])
