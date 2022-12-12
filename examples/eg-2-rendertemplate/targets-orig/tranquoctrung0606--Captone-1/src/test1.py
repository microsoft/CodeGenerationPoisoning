from flask import json, Flask, render_template, url_for, request, session, redirect, make_response, flash, jsonify
from flask_socketio import SocketIO
from flaskext.mysql import MySQL


import bcrypt
from flask_pymongo import PyMongo
from pymongo import MongoClient

app = Flask(__name__, static_url_path='/static')

app.config['SECRET_KEY'] = 'jsbcfsbfjefebw237u3gdbdc'
socketio = SocketIO(app)
app.secret_key = "super secret key"
mysql = MySQL()


app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = '1234'
app.config['MYSQL_DATABASE_DB'] = 'Postlist'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)


connection = MongoClient('mongodb://localhost:27017/')
dbs = connection.chatbot
col_traindata = dbs.questiondata
col_answerdata = dbs.answerdata
col_user = dbs.users

app.config['MONGO_DBNAME'] = 'chatbot'
app.config['MONGO_URI'] = 'mongodb://localhost:27017/chatbot'

mongo = PyMongo(app)

@app.route('/index')
def index():
    list = mongo.db.questiondata.find().limit(10)
    return render_template('a.html', list = list)
app.run(debug=True)