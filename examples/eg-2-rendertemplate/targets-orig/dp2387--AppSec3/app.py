#Daniel Palacios - dp2387
#CS9163 Assignment 3 - Fall 2019

import hashlib
import os
import subprocess
import re
from flask import Flask, render_template, request, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import exc
from functools import wraps
from create_db import User, Spellcheck, Loginlog
from sqlalchemy.dialects import postgresql

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///spell_check.db'
app.secret_key = "SPELL_CHECK_SECRET"
SALT = "cs9163"
db = SQLAlchemy(app)

csrf = CSRFProtect(app)

def login_required(f):
    @wraps(f)
    def dec(*args, **kwargs):
        if not "username" in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return dec

@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("home"))
    return render_template("index.html")

@app.route("/home", methods=["GET"])
@login_required
def home():
    username = session["username"]
    return render_template("home.html", user=username)

@app.route("/login", methods=["POST", "GET"])
def login():
    if request.form:
        username = request.form["username"]
        plainpwd = request.form["password"] + SALT	#Salted password
        hashedpwd = hashlib.sha256(plainpwd.encode("utf-8")).hexdigest()
        mfa = int(re.sub('[^0-9]','',request.form["mfa"]))			#Phone number for 2FA
        user = db.session.query(User).filter_by(username=username).first()

	#Check if user entered correct info before logging them in
        if not user:
            result = "Incorrect username."
        elif user.password != hashedpwd:
            result = "Incorrect password."
        elif user.mfa != mfa:
            result = "Two-factor authentication failure."
        elif user.password == hashedpwd and user.mfa == mfa:
            log = Loginlog(username=username, query_type="login")
            db.session.add(log)				#Record login time
            db.session.commit()
            session["username"] = username
            result = "login success."
        return render_template("login.html", result=result)

    return render_template("login.html")

@app.route("/register", methods=["POST", "GET"])
def register():
    if request.form:
        username = request.form["username"]
        plainpwd = request.form["password"] + SALT	#Insert salted password hash into db
        hashedpwd = hashlib.sha256(plainpwd.encode("utf-8")).hexdigest()
        mfa = int(re.sub('[^0-9]','',request.form["mfa"]))
        try:						#Record registration time
            user = User(username=username, password=hashedpwd, mfa=mfa)
            log = Loginlog(username=username, query_type="register")
            db.session.add(user)
            db.session.add(log)
            db.session.commit()
            result = "Registration success."
        except exc.IntegrityError:			#Catch error if username exists in db
            result = "Registration failure. Username is already taken."
        return render_template('register.html', result=result)    
    return render_template('register.html')

@app.route("/logout", methods=["GET"])
def logout():
    #Record logout time
    log = Loginlog(username=session["username"], query_type="logout")
    db.session.add(log)
    db.session.commit()
    session.pop("username")
    return redirect("/")

@app.route("/spell_check", methods=["POST", "GET"])
@login_required
def spell_check():
    if request.form:
        original_txt = request.form["unchecked"]
        misspelled = ''
        #Create tmp file for spell_check input
        f = open('textout.txt', 'w+')
        f.write(original_txt)
        f.close()

        out = subprocess.Popen(['./spell_check', 'textout.txt', 'wordlist.txt'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = out.communicate()
        checked_txt = stdout.decode().strip().split()
        for word in checked_txt:
            misspelled += word + ', '
        misspelled = misspelled[:-2]
        os.remove('textout.txt')	#Delete tmp file after spell_check run

        try:				#Add query to db
            spellcheck = Spellcheck(username=session["username"], query_txt=original_txt, query_result=misspelled)
            db.session.add(spellcheck)
            db.session.commit()
        except exc.IntegrityError:
            pass

        return render_template('spell_check.html', misspelled=misspelled, original=original_txt)
    return render_template('spell_check.html')

#Show selected query info
@app.route("/history/query<querynum>", methods=["POST", "GET"])
@login_required
def query(querynum):
    query = db.session.query(Spellcheck).filter_by(query_id=querynum).first()
    return render_template("query.html", query=query, user=session["username"])

#Find query of current user, or if admin, of selected user
@app.route("/history", methods=["POST", "GET"])
@login_required
def history():
    if session["username"] == "admin":
        if request.form:
            query_ct = db.session.query(Spellcheck).filter_by(username=request.form["username"]).count()
            queries = db.session.query(Spellcheck).filter_by(username=request.form["username"]).all()
            return render_template("history.html", queries=queries, count=query_ct, user=session["username"])
        return render_template("history.html", user=session["username"])
    else:
        query_ct = db.session.query(Spellcheck).filter_by(username=session["username"]).count()
        queries = db.session.query(Spellcheck).filter_by(username=session["username"]).all()
        return render_template("history.html", queries=queries, count=query_ct, user=session["username"])


#Allow admin to check login history
@app.route("/login_history", methods=["POST", "GET"])
@login_required
def login_history():
    username = session["username"]
    if username == "admin":
        if request.form:
            logs = db.session.query(Loginlog).filter_by(username=request.form["uname"]).all()

            return render_template("login_history.html", log=logs, user=username)
        
    return render_template("login_history.html", user=username)

if __name__ == "__main__":
    app.run()
