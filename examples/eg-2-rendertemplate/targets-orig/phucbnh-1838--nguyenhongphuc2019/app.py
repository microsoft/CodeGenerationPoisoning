import os
import time

from flask import Flask, render_template, redirect, url_for, flash
from wtform_fields import *
from models import *
from passlib.hash import pbkdf2_sha256
from flask_login import LoginManager, login_user, current_user, login_required, logout_user
from flask_toastr import Toastr
from flask_socketio import SocketIO, send, join_room, leave_room
from search_bot import wiki_how
from datetime import datetime
from profanity_word import profanity_word

SECRET_KEY = os.environ.get('SECRET_KEY')

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['TOASTR_PROGRESS_BAR'] = 'false'

db = SQLAlchemy(app)
login = LoginManager(app)
login.init_app(app)
toastr = Toastr(app)
socketio = SocketIO(app, manage_session=False)
ROOMS = ['news', 'bot']


@login.user_loader
def load_user(user_id):
    if user_id is not None:
        return User.query.get(user_id)
    return None


@app.route('/signup', methods=['GET', 'POST'])
def index():
    flash('Welcome you join with us')
    reg_form = RegistrationForm()
    form_valid = reg_form.validate_on_submit()
    if form_valid:
        username = reg_form.username.data
        password = reg_form.password.data
        hash_password = pbkdf2_sha256.hash(password)
        user = User(username=username, password=hash_password)
        db.session.add(user)
        db.session.commit()
        flash('Registered successfully, now you can login with us', 'success')
        return redirect(url_for('login'))
    return render_template('index.html', form=reg_form)


@app.route('/', methods=['GET', 'POST'])
def login():
    login_form = LoginForm()
    if current_user.is_anonymous and current_user.is_authenticated:
        return render_template('login.html', form=login_form)
    if current_user.is_authenticated:
        return redirect(url_for('chat'))
    form_valid = login_form.validate_on_submit()
    if form_valid:
        user_object = User.query.filter_by(username=login_form.username.data).first()
        login_user(user_object, remember=True)
        return redirect(url_for('chat'))
    return render_template('login.html', form=login_form)


@app.route('/chat', methods=['GET', 'POST'])
@login_required
def chat():
    rooms = Room.query.all()
    return render_template('chat.html', username=current_user.username, rooms=rooms)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Bye and see you soon', 'success')
    return redirect(url_for('login'))


@socketio.on('payload')
def on_message(data):
    msg = profanity_word(data["msg"], 'vi')
    username = data["username"]
    roomname = data["room"]
    time_stamp = time.strftime('%b-%d %I:%M%p', time.localtime())
    send({'username': username, 'msg': msg, 'time_stamp': time_stamp, 'room': roomname}, room=roomname)
    room_id = Room.query.filter_by(roomname=roomname).first().id
    user_id = User.query.filter_by(username=username).first().id
    message = Messages(user_id=user_id, room_id=room_id, msg=msg, sent_at=datetime.now())
    if roomname != 'bot':
        db.session.add(message)
        db.session.commit()
    if roomname == 'bot':
        summary, set_keyword_related = wiki_how(msg, 'vi')
        send({'username': 'From system with love', 'msg': summary, 'time_stamp': time_stamp}, room=roomname)


@socketio.on('join')
def on_join(data):
    username = data["username"]
    room = data["room"]
    join_room(room)
    messages_in_room = []
    room_id = Room.query.filter_by(roomname=room).first().id
    for instance in Messages.query.filter_by(room_id=room_id).all():
        mes_username = User.query.filter_by(id=instance.user_id).first().username
        mes = {
            'username': mes_username,
            'room': room,
            'time_stamp': instance.sent_at.strftime('%Y-%m-%d %H:%M'),
            'msg': instance.msg
        }
        messages_in_room.append(mes)
    time_stamp = time.strftime('%b-%d %I:%M%p', time.localtime())
    send({
            'msg': 'WE [APPRECIATE] ' + username + ' HAS JOIN THE ' + room + ' CHAT',
            'time_stamp': time_stamp,
            'username': 'From system with love',
            'room': room,
            'has_join': 'true',
            'messages_in_room': messages_in_room
    }, room=room)


@socketio.on('leave')
def on_leave(data):
    username = data['username']
    room = data['room']
    leave_room(room=room)
    time_stamp = time.strftime('%b-%d %I:%M%p', time.localtime())
    send({
        'msg': 'WE [ANNOUNCED] ' + username + ' HAS LEFT THE ' + room + ' CHAT',
        'username': 'From system with love',
        'has_join': 'false',
        'time_stamp': time_stamp
    }, room=room)


if __name__ == '__main__':
    app.run()
