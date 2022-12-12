# import socketio as socketio
from flask import Flask, flash
from flask import render_template
from flask import request, session, redirect, url_for
from flask_login import LoginManager
from flask_socketio import SocketIO, emit

login_manager = LoginManager()

app = Flask(__name__)
app.config["SECRET_KEY"] = "yousecntuch"
app.debug = True
login_manager = login_manager.init_app(app)

socketio = SocketIO(app)


@app.route('/')
def index():
    return '<h1>This shows the simplest home page, it renders a simple header</h1>'


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        my_dict = {'Clyde': 'I am Clyde', 'Barry': 'I am Barry'}
        flash('Logged in successfully.')
        session['username'] = request.form['username']
        print(session['username'])
        flash('Logged in successfully.')
        try:
            return f"{my_dict[session['username']]}"
        except:
            return f"Invalid Login"
    return '''
        <form method="post">
            <p><input type=text name=username>
            <p><input type=submit value=Login>
        </form>
    '''


@app.route('/clyde')
def info():
    clyde_str = "<h1>My name is Clyde</h1><p>My session user name is " + session['username']
    return clyde_str


@app.route('/user/<name>')
def user(name):
    return f"<h1>This is {name}'s page</h1><p style='font-size:30px;'>10 &#9824;</p>"


@app.route('/raw_table')
def raw_table():
    return render_template('test3.html')


@app.route('/da_var')
def some_func():
    my_var = {'name': 'Barry Bornstein',
              'favorite_bet': '20 cents'}
    print(my_var['name'])
    return render_template('test_var.html', my_variable=my_var)


@socketio.on('my_event')
def test_message(message):
    emit


if __name__ == '__main__':
    socketio.run(app, debug=True)
