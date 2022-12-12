from flask import Flask, g, session, redirect, url_for, render_template, request
from flask_restful import Resource, Api
from flask_socketio import SocketIO, emit, send
from .models import initialize_db
from .views import initialize_routes
from .socket import *


# wtf forms socket test
from flask_wtf import Form
from wtforms.fields import StringField, SubmitField
from wtforms.validators import Required


app = Flask(__name__)
app.config.from_object('config')
app.config['SECRET_KEY'] = 'secret!'

api = Api(app)
initialize_routes(api)
initialize_socket(app)
initialize_db(app)

# socket io test


class LoginForm(Form):
    """Accepts a nickname and a room."""
    name = StringField('Name', validators=[Required()])
    room = StringField('Room', validators=[Required()])
    submit = SubmitField('Enter Chatroom')


@app.route('/', methods=['GET', 'POST'])
def index():
    """Login form to enter a room."""
    form = LoginForm()
    if form.validate_on_submit():
        session['name'] = form.name.data
        session['room'] = form.room.data
        return redirect(url_for('chat'))
    elif request.method == 'GET':
        form.name.data = session.get('name', '')
        form.room.data = session.get('room', '')
    return render_template('index.html', form=form)


@app.route('/chat')
def chat():
    """Chat room. The user's name and room must be stored in
    the session."""
    name = session.get('name', '')
    room = session.get('room', '')
    if name == '' or room == '':
        return redirect(url_for('index'))
    return render_template('chat.html', name=name, room=room)
