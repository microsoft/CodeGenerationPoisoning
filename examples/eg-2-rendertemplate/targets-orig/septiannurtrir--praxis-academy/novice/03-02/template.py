#template html
from flask import Flask, render_template
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html') #contoh statis file

@app.route('/profile/<username>')
def show_profile(username):
    return 'Selamat datang di laman profile %s' % username