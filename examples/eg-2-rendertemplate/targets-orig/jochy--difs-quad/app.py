from flask import Flask, render_template, session
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)


@app.route("/")
def index():
    get_session['dino'] = 'TREX'
    return render_template('index.html', title='Hello world !')


def get_app():
    return app


def get_session():
    return session
