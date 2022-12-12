#!/usr/bin/python
# -*- coding: utf-8 -*-

from flask import Flask,render_template, redirect, url_for, flash, session
from dbase.mysql import Employees
import pymysql
from flask import request
from flask import render_template
#from flask_bootstrap import Bootstrap
from src.tools import logs
from src.model import user
from dbase.mysql import config
import re

app = Flask(__name__)
app.secret_key = "secret key"
logga = logs.get_logger(logs.INFO)
pattern = r'^[0-9]*'
MAX = 499999

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/employees/<int:empNum>',methods=['GET'])
def get_users(empNum):
    if not empNum:
        error = 'Empty employee number'
        logga.info("".format(error))

    if empNum >= MAX:
        error = 'Worng employee number '
        logga.info("".format(error))
    results = []
    query = """ select e.emp_no, e.first_name, e.last_name,d.dept_name as current_department, s.salary from employees e
left join current_dept_emp cde on cde.emp_no = e.emp_no
left join departments d on d.dept_no = cde.dept_no
left join salaries s on s.emp_no = e.emp_no
where e.emp_no = {empNum}"""
    try:
        db = pymysql.connect(host='127.0.0.1', port=3307, user='root', passwd='college', db='employees')
        cursor = db.cursor()
        cursor.execute(query.format(empNum=empNum))
        res = cursor.fetchall()
    except Exception as e:
        logga.error(e)
        return "Something went wrong, Please try again"

    if not res:
        logga.info('No Information Found')
        return 'No Information Found'

    for r in res:
        results.append(r)
        print ("Database version : {} ".format(r))

    labels = [l[0] for l in cursor.description]
    db.close()
    return render_template('employees.html',content=results,lables=labels)

@app.route('/employees')
def get_deafult():
    results = []
    query = """ 
    select * from employees limit 10;
    """

    try:
        db=pymysql.connect(host='127.0.0.1', port=3307, user='root', passwd='college', db='employees')#**config)
        cursor = db.cursor()
        cursor.execute(query)
        res = cursor.fetchall()
    except Exception as e:
        logga.error(e)
        return "Something went wrong, Please try again"

    if not res:
        logga.info('No Information Found')
        return 'No Information Found'

    for r in res:
        results.append(r)

    labels = [str(l[0]) for l in cursor.description]

    db.close()

    return render_template('employees.html',content=results,lables=labels)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        if valid_login(request.form['userid'], request.form['password']):
            flash("logged in！")
            session['userid'] = request.form.get('userid')
            logga.info("{}:{}".format(request.form.get('userid'), 'Log in Success'))
            return render_template('welcome.html', error=error)
        else:
            error = 'Wrong userid or Password'
            logga.error("{}:{}".format(request.form.get('userid'),error))
            return render_template('login.html', error=error)
    return render_template('login.html', error=error)

def valid_login(userid,password):
    print(userid)
    try:
        userid = int(userid)
    except Exception as e:
        logga.error(e)

    if userid not in user.Users_Credentials.keys() and re.match(pattern,userid):
        token = user.Users_Credentials['any']
        if token == password:
            return True
    if password == user.Users_Credentials[userid]:
        return True

    return False


if __name__ == '__main__':
    app.run("0.0.0.0", port=80,)
