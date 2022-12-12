from flask import render_template
from flask import send_from_directory
from flask import request
import flask
from datastore import insert


def serveOrder(req):
    print(req.cookies.get('email'))
    return render_template('order.html')


def processOrder(req):
    # print(req.data.decode())
    insert(req.cookies.get('email'), req.data.decode())
    return flask.jsonify({'status': 'Ok'})
