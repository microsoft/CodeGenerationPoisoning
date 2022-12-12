#from flask import Flask, render_template
# import libraries
import os
from flask import Flask, flash, render_template, request, session
from sqlalchemy.orm import sessionmaker
# Here we are importing the Flask module and creating a Flask web server from the Flask module.
# session by flask refers to http session within view (@app.route('/...')

#import own generated files or database
from investmentGame.db import db_engine_creation, Base
from investmentGame.User import User
import investmentGame.Portfolio

# create the SQL database
engine, session_factory = db_engine_creation()
Base.metadata.create_all(engine)
app = Flask(__name__)
# _name means this current file. In this case, it will be web_gui.py. This file represents my web application
# We are creating an instance of the Flask class and calling it app. Here we are creating a new web application.


# if you are logged in, the home screen will be shown, if you are not logged in, you will have to login
@app.route('/')
# default page, below function will be activated if default page is reached
def home():
    if not session.get('logged_in'):
        return render_template('login.html')
    else:
        return render_template("home.html")

@app.route('/about')
# default page, below function will be activated if default page is reached
def about():
    return render_template("about.html")

@app.route('/portfolio')
# default page, below function will be activated if default page is reached
def portfolio():
    return render_template("portfolio.html")

# validation of login variables if you have to login
# login user name = admin, and password is password
@app.route('/login', methods=['POST','GET'])
def user_login():
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        s = session_factory()
        query = s.query(User).filter(User.name.in_([name]), User.password.in_([password]))
        result = query.first()
        if result:
            session['logged_in'] = True
        elif name == 'admin' and password == 'password':
            session['logged_in'] = True
        else:
            flash('Wrong password')
    return home()


@app.route("/logout")
def logout():
    session['logged_in'] = False
    return home()


if __name__ == '__main__':
    app.secret_key = os.urandom(12)
    app.run(debug=True)