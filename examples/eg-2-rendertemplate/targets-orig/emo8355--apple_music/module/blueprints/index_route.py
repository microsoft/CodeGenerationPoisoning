from flask import Blueprint, render_template, request, url_for, redirect, make_response
from sqlalchemy.sql.expression import bindparam
from .. import db
from ..Src.user import user
import jwt
import datetime


main = Blueprint("main", __name__)


@main.route("/", methods=['get'])
def index():
    try:
        newuser = user(name="admin", email="123@123.123", password="123123")
        newuser2 = user(name="admin2", email="1233@1233.1233",
                        password="123123")
        db.session.add(newuser)
        db.session.add(newuser2)
        db.session.commit()
        return render_template("login.html")
    except:
        return render_template("login.html")


@main.route("/login", methods=["post"])
def login():
    login_user = request.form
    print(login_user)
    if not login_user or not login_user['email'] or not login_user['password']:
        return make_response('Could not verify', 401, {'WWW-Authenticate': 'Basic realm = "Login Required!"'})
    usr = user.query.filter_by(email=login_user['email']).first()

    if not usr:
        return make_response('Could not verify', 401, {'WWW-Authenticate': 'Basic realm = "Login Required!"'})

    if usr.password == login_user['password']:
        token = jwt.encode({'user_email': usr.email, 'exp': datetime.datetime.utcnow(
        ) + datetime.timedelta(hours=24)}, '***************')
        resp = make_response(redirect("/user/"))
        resp.set_cookie('user', token)
        return resp
    else:
        return render_template("login.html", err="password does not match, try again")

    return make_response('Could not verify', 401, {'WWW-Authenticate': 'Basic realm = "Login Required!"'})


@main.route("/signup", methods=["post"])
def signup():
    name = request.form['name']
    email = request.form['email']
    password = request.form['password']
    password_confirm = request.form['password_confirm']
    if password_confirm == password:
        newuser = user(name=name, email=email, password=password)
        db.session.add(newuser)
        db.session.commit()
        return render_template("login.html", ok="you can login now")
    else:
        return render_template("login.html", err="password does not match, try again")


@main.route("/logout", methods=['GET'])
def logout():
    resp = make_response(render_template("login.html"))
    user_id = request.cookies.get("user")
    resp.set_cookie('user', user_id, max_age=0)
    return resp
