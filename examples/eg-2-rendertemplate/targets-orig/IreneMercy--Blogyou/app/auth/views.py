from flask import render_template, request, redirect, url_for
from . import auth
from app.models import User
from flask_login import login_user,login_required, logout_user
from .. import mail
from flask_mail import Message

@auth.route('/login', methods=['POST','GET'])
def login():
    if request.method=='POST':
        form = request.form
        username = form.get("username")
        password = form.get("password")
        user = User.query.filter_by(username=username).first()
        if user == None:
            error = "User with that username  does not exist"
            return render_template('login.html', error=error)
        is_correct_password = user.check_password(password)
        if is_correct_password!=False:
            login_user(user)
            return redirect(url_for('main.home'))
            print('Username')
    return render_template('login.html')


@auth.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == "POST":
        form = request.form
        username = form.get("username")
        email = form.get("email")
        password = form.get("password")
        confirm_password = form.get("confirm_password")

        if username==None or password==None or email==None or password==None or confirm_password==None :
            error = "All fields are required"
            return render_template('signup.html', error=error)
        if " " in username:
            error = "Username should not contain space"
            return render_template('signup.html',erorr=error)
        if password != confirm_password:
            error = "Password does not match"
            return render_template("signup.html", error=error)
        else:
            user = User.query.filter_by(username=username).first()
            if user != None:
                error = "A user with that username already exist"
                return render_template('signup.html', error=error)

            user = User.query.filter_by(email=email).first()
            if user != None:
                error = "A user with that email already exist"
                return render_template('signup.html', error=error)
            user = User(username=username,email=email)
            user.set_password(password)
            user.save()
            return redirect(url_for("auth.login"))
        print(username)
    return render_template('signup.html')

@auth.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
