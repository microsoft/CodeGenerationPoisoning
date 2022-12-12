from flask import render_template,redirect,url_for,flash,request
from . import auth
from flask_login import login_required,current_user, login_user,logout_user
import re
from app.models import User

@auth.route('/login',methods=['GET','POST'])
def login():
    if request.method == 'POST':
        form = request.form
        username = form.get("username")
        password = form.get("password")

        user= User.query.filter_by(username=username).first()
        if user == None :
            error ="User with username does not exist"
            return render_template('login.html', error = error)
        is_correct_password = user.check_password(password)
        if is_correct_password == False:
            error ="User with  password does not exist"
            return render_template('login.html', error=error)
        login_user(user)
        return redirect(url_for('main.home'))
    return render_template('login.html', title='Login')


@auth.route('/registration', methods=['POST','GET'])
def register():
    if request.method == 'POST':
        form = request.form
        firstname = form.get("firstname")
        secondname = form.get("secondname")
        username = form.get("username")
        email = form.get("email")
        password = form.get("password")
        confirm_password = form.get("confirm_password")


        if username==None or password==None or confirm_password==None or email==None:
            error = "username,password and email are required"
            return render_template('register.html', error=error)

        

        # for validating an Email 
        regex = '^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$'
        if  re.match(regex,email)== None:
            error = "Invalid Email.Please use correct email format"
            return render_template('register.html',error=error)

        if password != confirm_password:
            error = " Passwords Not a match"
            return render_template('register.html',error=error)
        else:
            user = User.query.filter_by(username= username).first()
            if user!= None:
                error = "Username exists"
                return render_template('register.html', error = error)
            user = User.query.filter_by(email=email).first()
            if user!= None:
                error = "Email exists"
                return render_template('register.html', error = error)

            user = User(firstname=firstname,secondname=secondname,username=username,email=email)
            user.set_password(password)
            user.save()
            return redirect(url_for("auth.login"))
    
    
    return render_template('register.html',title='Register')


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been successfully logged out')
    return redirect(url_for("main.home"))
