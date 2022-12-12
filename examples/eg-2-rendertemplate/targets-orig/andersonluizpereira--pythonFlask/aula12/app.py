from flask import Flask, render_template, request, session, redirect, url_for
import json

app = Flask(__name__, template_folder='templates')
app.secret_key = "123456"

@app.route("/")
def index():
    username = ''
    if 'username' in session:
        username = session['username']
    return render_template('index.html', username = username)

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST' and request.form['username'] != '':
        session['username'] = request.form['username']
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route("/logout")
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route("/setsession/<s>")
def setsession(s):
    session['username'] = s
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run()