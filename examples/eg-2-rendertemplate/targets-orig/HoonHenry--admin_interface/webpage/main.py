from flask import render_template, Flask, request, redirect
from webpage.functions import *


app = Flask("adminEnv")

db = {}


@app.route("/")
def home():
    return render_template("user_list.html")


@app.route('/register')
def register():
    user_id = request.args.get('userid')
    user_pw = request.args.get('userpw')
    user_name = request.args.get('username')
    user_email = request.args.get('useremail')
    user_phone = request.args.get('phonenum')
    clearance = request.args.get('rank')
    user = get_userinfo(id=user_id, pw=user_pw, name=user_name,
                        email=user_email, phone=user_phone, cl=clearance)
    if user:
        existings= db.get(user)
        if existings:
            pass

    return render_template('user_list.html', users=user)


@app.route("/result")
def result():
    user_id = request.args.get('userid')
    user_pw = request.args.get('userpw')
    user_name = request.args.get('username')
    user_email = request.args.get('useremail')
    user_phone = request.args.get('phonenum')
    clearance = request.args.get('rank')
    user = get_userinfo(id=user_id, pw=user_pw, name=user_name,
                        email=user_email, phone=user_phone, cl=clearance)

    return render_template('result.html', userid=user['id'],
                           username=user['name'])


app.run(host="0.0.0.0")
