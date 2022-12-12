#Kacper Skelnik 291566
#Wojciech Tyczyński 291563
from flask import Flask, render_template, redirect, url_for, request
from connection import Connection
from flask_sqlalchemy  import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import time
from subprocess import call
import os

REGISTRATION = "!726567697374726174696f6e"  # !HEX use to something like handshake
CREATED = "!63726561746564"
LOGIN = "!6c6f67696e"
CORRECT = "!636f7272656374"
CHAT = "!636861745f746f"
NOTHING = "!6e6f7468696e67"
SEND = "!53656e6453656e64"
FRIENDS = "!667269656e6473"
ADDED = "!6164646564206164646564"
DISCONNECT = "!444953434f4e4e454354"
INCORRECT = "!696e636f7272656374"
USER = "!555345525f5f5f55534552"
EXIST = "!45584953545f5f4558495354"
OK = "!4f4b5f4f4ba"
IS_FRIEND = "!69735f667269656e64"
READY = "72656164795f5f7265616479"

forbidden = [REGISTRATION, CREATED, LOGIN, CORRECT, CHAT, NOTHING, SEND, FRIENDS,  # Array of forbidden messages because
             ADDED, DISCONNECT, INCORRECT, USER, EXIST, OK, IS_FRIEND, READY]      # of handshakes

server = os.environ["server"]
Connection = Connection(server)   # create Connection object
Connection.connect()        # connect app with server

# Configure application
app = Flask(__name__)       # declaration of flask app
app.config.update(dict(     # add secret key and csrf secret key for security reasons
    SECRET_KEY="powerful secretkey",
    WTF_CSRF_SECRET_KEY="a csrf secret key"
))
app.debug = True            # set debug True

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users_client.db'  # Database name
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False                 # disable sqlalchemy warnings
db = SQLAlchemy(app)                                                 # connect database with app

# Configure login manager
login_manager = LoginManager()      # object used to hold the settings used for logging in
login_manager.init_app(app)         # connect login_manager with app
login_manager.login_view = 'login'  # set name of the log in view

from wtform_fields import *


# Create local data base to store info about login users
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(25), unique=True, nullable=False)
    password = db.Column(db.String(), nullable=False)


# Configure login decoratorexcept
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))     # return User data base object by id


def writePidFile():
    """create pid file of the process"""
    pid = str(os.getpid())                  # get pid as string
    f = open('app.pid', 'w')                # open file
    f.write(pid)                            # write pid to file
    f.close()                               # close file


writePidFile()      # execute writePidFile


@app.route('/', methods=['POST', 'GET'])            # set route and methods to communicate with page
def index():
    registration_form = RegistrationForm()          # declaration of wtf_form used on page
    if registration_form.validate_on_submit():      # if user click on the button
        username = registration_form.username.data  # get username from username form
        password = registration_form.password.data  # get password from password form

        Connection.send(REGISTRATION)               # send notification that user wants to login
        Connection.send(username)                   # send username to server
        Connection.send(password)                   # send password to server

        if Connection.recv() == CREATED:                                # if server return CREATED
            new_user = User(username=username, password=password)       # create User object
            db.session.add(new_user)                                    # add new User object to data base
            db.session.commit()                                         # commit changes to data base
            return redirect(url_for('login'))                           # redirect to login page

    return render_template('index.html', form=registration_form)        # render template


@app.route('/login', methods=['POST', 'GET'])           # set route and methods to communicate with page
def login():
    login_form = LoginForm()                            # declaration of wtf_form used on page
    if login_form.validate_on_submit():                 # if user click on the button
        if Connection.recv() == CORRECT:                # if server return CORRECT
            user = User.query.filter_by(username=login_form.username.data).first()  # try to query base on from data
            if user:                    # if user object exist
                Connection.recv()       # receive nothing (because server can send INCORRECT)
                login_user(user)        # login user by login_manager
            else:
                data = Connection.recv()                                # receive nothing (because server can send INCORRECT)
                new_user = User(username=data[1], password=data[2])     # create new user object
                db.session.add(new_user)                                # add new User object to data base
                db.session.commit()                                     # commit changes to data base
                login_user(new_user)                                    # login user by login_manager
            return redirect(url_for('chat'))                            # redirect to chat page

    return render_template("login.html", form=login_form)               # render template


Ready_to_update = False         # global variable False if chat receive some data True if buffer is free


@app.route('/get_messages')                  # set route
def get_messages():
    global Ready_to_update                   # reference to global variable
    try:
        messages = []                        # messages array declaration
        if Ready_to_update:                  # base on global variable
            Connection.send(READY)           # send READY to server
            messages_from = Connection.recv()       # receive messages for login user
            messages_to = Connection.recv()         # receive messages from login user
            messages = messages_from + messages_to  # create message array
            messages.sort(key=lambda x: x[4])       # sort messages base on date
        return render_template('messages.html', name=current_user.username, messages=messages)      # render template
    except:
        print("There was something issue with loading messages")
        Ready_to_update = False      # set global Ready_to_update
        Connection.send(DISCONNECT)  # disconnect client
        time.sleep(1)                # wait 1 sec
        call("./restart.sh", shell=True)    # call bash script which will kill current process and run new process


@app.route('/chat', methods=['POST', 'GET'])        # set route and methods to communicate with page
@login_required                                     # pass user if login
def chat():
    global Ready_to_update                          # reference to global variable

    try:
        Ready_to_update = False                     # set global variable to False

        Connection.send(CHAT)                       # send CHAT to server
        Connection.send(current_user.username)      # send current username

        chat_form = ChatForm()                      # declaration of wtf_form used on page
        chat_form.friend.choices = Connection.recv()                # receive list of user friends
        chat_form.friend.default = chat_form.friend.choices[0]      # set default chose of SelectField to 0

        user_to_send = dict(chat_form.friend.choices).get(chat_form.friend.data)    # take user to send from SelectField

        if user_to_send:                            # if user_to_send exist
            user_to_send = user_to_send.split()[1]  # take data from SelectField and pull only username
            Connection.send(user_to_send)           # send user_to_send to server
            messages_from = Connection.recv()       # receive messages for login user
            messages_to = Connection.recv()         # receive messages from login user
        else:
            Connection.send(" ")                    # send " " (it is ok, because username have to be longer than 3)
            messages_from = Connection.recv()       # receive messages for login user
            messages_to = Connection.recv()         # receive messages from login user

        messages = messages_from + messages_to      # create message array
        messages.sort(key=lambda x:x[4])            # sort messages base on date

        if request.method == 'POST':                # if request method is to post data
            if request.form['action'] == 'Send':    # if user click on the button 'Send'
                message = chat_form.text.data       # take data form form
                if message != "" and message not in forbidden:  # if message is not empty or in forbidden array
                    if user_to_send:                # if user_to_send exist
                        Connection.send(message)    # send message to server

                chat_form.text.data = ""            # clear form

            if request.form['action'] == 'Add new friend':      # if user click on the button 'Add new friend'
                return redirect(url_for('friends'))             # redirect to friends page

        Ready_to_update = True                      # set global variable to True

        return render_template('chat.html', form=chat_form, name=current_user.username, messages=messages)
    except:
        print("There was something issue with chat")    # the same like is in get_messages()
        Ready_to_update = False
        Connection.send(DISCONNECT)
        time.sleep(1)
        call("./restart.sh", shell=True)


@app.route('/friends', methods=['POST', 'GET'])         # set route and methods to communicate with page
@login_required                                         # pass user if login
def friends():
    friends_form = FriendsForm()                        # declaration of wtf_form used on page

    if friends_form.validate_on_submit():               # if user click on the button
        if Connection.recv() == ADDED:                  # if receive ADDED from server
            return redirect(url_for('chat'))            # redirect to chat page

    return render_template("friends.html", form=friends_form)


@app.route('/logout', methods=['GET'])
def logout():
    Connection.send(DISCONNECT)     # logout client
    return "You are log out"


if __name__ == '__main__':
    app.run(debug=True)             # run app