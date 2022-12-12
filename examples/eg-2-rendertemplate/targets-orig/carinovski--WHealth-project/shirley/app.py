from flask import (Flask, render_template, make_response, url_for, request,
                  redirect, flash, session, send_from_directory, jsonify
                  )
from werkzeug.utils import secure_filename
import pymysql
import cs304dbi as dbi
dsn = dbi.cache_cnf()
dbi.use('whealth_db')
 
app = Flask(__name__)
 
import random
 
app.secret_key = 'your secret here'
# replace that with a random key
app.secret_key = ''.join([ random.choice(('ABCDEFGHIJKLMNOPQRSTUVXYZ' +
                                         'abcdefghijklmnopqrstuvxyz' +
                                         '0123456789'))
                          for i in range(20) ])
 
# This gets us better error messages for certain common request errors
app.config['TRAP_BAD_REQUEST_ERRORS'] = True
 
staffID = 1409
 
@app.route('/')
def index():
   return render_template('main.html')
 
@app.route('/suggest/', methods = ["GET", "POST"])
def suggest():
    if request.method == "GET":
        return render_template('suggest.html')
 
@app.route('/update/', methods = ["GET", "POST"])
def update():
    if request.method == "GET":
        return render_template('update.html')
  
@app.route('/search/', methods = ['GET'])
def search():
    if request.method == "GET":
        return render_template('search.html')
 
if __name__ == '__main__':
   import sys, os
   dbi.cache_cnf()  # only once
   dbi.use('wmdb')
   port = os.getuid()
   app.debug = True
   app.run('0.0.0.0',port)
