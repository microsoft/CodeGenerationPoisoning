from flask_login import login_user, logout_user, login_required, current_user

from . import auth
from .forms import RegisterationForm
from flask import render_template, redirect, url_for, flash, current_app, request

from .send_mail import send_mail
from .. import db
from ..models import User, Todo
from .forms import LoginForm


@auth.route('/')
def index():
    return render_template('auth/index.html')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.verify_password(form.password.data):
            login_user(user)
            user.ping()
            flash('用户登录成功', category='success')
            return redirect(url_for('todo.list'))
        else:
            flash('用户登录失败', category='error')
            return redirect(url_for('auth.login'))

    return render_template('auth/login.html', form=form)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('用户注销成功', category='success')
    return redirect(url_for('auth.index'))


@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterationForm()
    if form.validate_on_submit():
        user = User()
        user.username = form.username.data
        user.email = form.email.data
        user.password = form.password.data
        db.session.add(user)
        # 获得验证信息
        token = user.generate_confirmation_token()
        # print(user.email)
        send_mail(user.email, '欢迎使用任务清单管理系统', 'auth/confirm',
                  user=user, token=token
                  )
        flash('平台验证消息已经发送到你的邮箱, 请确认后登录.', category='success')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)


@auth.route('/confirm/<token>')
@login_required
def confirm(token):
    if current_user.confirmed:
        return redirect(url_for('todo.list'))
    if current_user.confirm(token):
        print(current_user.username)
        flash('验证邮箱通过', category='success')
        return redirect(url_for('todo.list'))
    else:
        print(current_user)
        flash('验证连接失效', category='error')
        return render_template('auth/confirm_failed.html')


@auth.before_app_request
def before_request():
    # 用户已登录但未认证，访问的是资源路径的时候，返回未认证页面

    # print(request.endpoint)

    # print('************')
    # print(request.endpoint)
    # print('************')

    if current_user.is_authenticated \
            and not current_user.confirmed \
            and request.endpoint[:5] != 'auth.' \
            and request.endpoint != 'static':
        return redirect(url_for('auth.unconfirmed'))


@auth.route('/unconfirmed')
@login_required
def unconfirmed():
    # 如果当前用户是匿名用户或者已经验证的用户, 则访问主页, 否则进入未验证界面;
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for('todo.list'))
    token = current_user.generate_confirmation_token()
    return render_template('auth/unconfirmed.html')


@auth.route('/reconfirm')
@login_required
def resend_confirmation():
    token = current_user.generate_confirmation_token()
    try:
        send_mail(current_user.email, '请激活你的任务管理平台帐号',
                  'auth/confirm', user=current_user, token=token)
    except Exception as e:
        print(e)
        flash(str(e), category='error')
        return redirect(url_for('auth.register'))
    else:
        flash('新的平台验证消息已经发送到你的邮箱, 请确认后登录.', category='success')
        print('邮件发送成功')
        return redirect(url_for('auth.login'))
