from . import auth
from flask import request, redirect, url_for, flash, render_template
from flask_login import login_user, login_required, logout_user
from app import db
from app.auth.forms import RegistrationForm,LoginForm
from app.models import User

@auth.route('/')
def auth_home():
    return 'auth_home'


@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User()
        user.email = form.email.data
        user.username = form.username.data
        user.password = form.password.data
        db.session.add(user)
        flash('注册成功, 请登录')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)


@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
    # 调用 Flask-Login 中的 login_user() 函数,在用户会话中把用户标记为已登录。
    # login_user() 函数的参数是要登录的用户,以及可选的“记住我”布尔值,“记住我”也在表单中填写。
            login_user(user)
            return redirect(request.args.get('next') or url_for('auth.login'))
        flash('无效的用户名和密码.')
    return render_template('auth/login.html', form=form)

@auth.route('/logout')
@login_required
def logout():
   logout_user()
   flash('用户注销成功.')
   return redirect(url_for('auth.login'))