from flask import Blueprint, render_template, abort, flash, request
from jinja2 import TemplateNotFound
import urllib.request 
import os.path
from os import remove
from requests import get
from hashlib import sha3_256
import pymysql.cursors

search = Blueprint('search', __name__, template_folder='templates')

def connect_to_db():
    return pymysql.connect(host='maria',
                            user='root',
                            password='changeme',
                            db='tubehub',
                            charset='utf8mb4',
                            cursorclass=pymysql.cursors.DictCursor)

@search.route('/', methods=['POST', 'GET'])
def show_search():
    try:
        if request.method == 'POST':
            POST_search = str(request.form['Search'])
             # Connect to database
            connection = connect_to_db()

            # check database for string
            try:
                with connection.cursor() as cur:
                    if POST_search[0] != "\'" and POST_search != '':
                        POST_search = POST_search + "\'"

                    sql = "SELECT title FROM video WHERE title=\'" + POST_search
                    cur.execute(sql)
                    data = cur.fetchall()
            except:
                abort(404)
            finally:
                connection.close()
            
        if request.method == 'GET':
            return render_template('/search/results.html')
        
        return render_template('/search/search.html', data=data)
    except TemplateNotFound:
        abort(404)

@search.route('/results', methods=['POST', 'GET'])
def show_results():
    try:
        if request.method == 'POST':
            POST_search = str(request.form['Search'])
             # Connect to database
            connection = connect_to_db()

            # check database for string
            try:
                with connection.cursor() as cur:
                    if POST_search[0] != "\'" and POST_search != '':
                        POST_search = POST_search + "\'"

                    sql = "SELECT title FROM video WHERE title=\'" + POST_search
                    cur.execute(sql)
                    data = cur.fetchall()
            except:
                abort(404)
            finally:
                connection.close()



        return render_template('/search/search.html')
    except TemplateNotFound:
        abort(404)
