# encoding: utf8

from flask import Blueprint, render_template, session, redirect, request, url_for, flash
from application.models import User
from application.extension import db
from werkzeug.security import check_password_hash


user_page = Blueprint('user_page', __name__)


@user_page.route('/users')
def users():
    if session.get('user_id'):
        users = User.query.all()
        return render_template('user/index.html', users=users)
    else:
        return redirect('/')


@user_page.route('/')
@user_page.route('/login', methods=['GET', 'PoSt'])
def login():
    if request.method == 'GET':
        return render_template('user/login.html')
    else:
        name = request.form.get('name')
        pwd = request.form.get('password')

        user = User.query.filter(User.username == name).first()

        if user and check_password_hash(user.password, pwd):
            session['user_id'] = user.id
            # return redirect(url_for('user_page.users'))
            return '1'
        else:
            flash('登陆失败')
            # return render_template('user/login.html')
            return '0'


@user_page.route('/users/<id>', methods=['GET', 'Post'])
def edit(id):
    user = User.query.get(id)

    if request.method == 'GET':
        return render_template('user/edit.html', user=user)
    else:
        username = request.form.get('username')
        password = request.form.get('password')
        gender = request.form.get('gender')

        user.username = username
        user.password = password
        user.gender = gender

        db.session.commit()
        flash('修改成功')

        return redirect('/users')

