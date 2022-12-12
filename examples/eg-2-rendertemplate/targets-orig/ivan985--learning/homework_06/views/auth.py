from werkzeug.exceptions import NotFound
from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user, login_user, logout_user
from logging import getLogger

from homework_06.views.auth_methods import *

# Все страницы раздела auth (авторизация и содержание, доступное только авторизованным пользователям)
logger = getLogger(__name__)

auth_app = Blueprint("auth_app", __name__)


# главная страница
@auth_app.route("/", endpoint="index")
def index():
    return render_template("auth/index.html")


# для страницы регистрации
@auth_app.route("/register/", methods=("GET", "POST"), endpoint="register")
def register():
    if current_user.is_authenticated:
        return redirect(url_for("auth_app.index"))

    if request.method == "GET":
        return render_template("auth/register.html")

    username, password = get_username_and_password()
    validate_username_unique(username)

    user = User(username, password)
    Session.add(user)

    try:
        Session.commit()
    except Exception:
        logger.exception("Failed to add user!")
        Session.rollback()

    login_user(user)
    return redirect(url_for("auth_app.index"))


# для страницы логина
@auth_app.route("/login/", methods=("GET", "POST"), endpoint="login")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("auth_app.index"))

    if request.method == "GET":
        return render_template("auth/login.html")

    username, password = get_username_and_password()

    user = Session.query(User).filter_by(username=username).one_or_none()
    if not (user and user.password == User.hash_password(password)):
        raise BadRequest("Username or password invalid!")

    login_user(user)
    return redirect(url_for("auth_app.index"))


# выход из системы
@auth_app.route("/logout/", methods=("GET", "POST"), endpoint="logout")
def logout():
    logout_user()
    return redirect(url_for("auth_app.index"))


# страница со списком произведений
@auth_app.route("/db_main/", endpoint="db_main")
def db_main():
    titles = title_list()
    return render_template("auth/db_main.html", titles = titles)


# страницы для конкретных произведений
@auth_app.route('/db_main/<int:title_id>/', endpoint='post')
def get_product(title_id):
    try:
        title_text, title_name = title_texts(title_id)
    except Exception:
        raise NotFound(f'There is no post #{title_id}')
    return render_template(
        'auth/post.html',
        title_text=title_text,
        title_name=title_name,
    )
