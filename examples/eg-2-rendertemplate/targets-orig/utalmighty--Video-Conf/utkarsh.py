from flask import Flask, render_template, request, redirect, url_for, flash
from flask_socketio import SocketIO, emit, send
import os
#import json5 as json
#import psycopg2 as postgres

database = []



con = Flask(__name__)
con.secretKey = os.environ.get('Secret_Key')
socket = SocketIO(con)


@con.errorhandler(404)
def errpage(e):
    return render_template('error.html')


@con.route('/about')
def about():
    return render_template('about.html')

@con.route('/')
def home():
    return render_template('Home.html')

@socket.on_error_default
def default_error_handler(e):
    print(str(e))

@socket.on('Credentials', namespace = '/private')
def Credentials(credential_json):
    if(credential_json['creator'] == True):
        for i in database:
            if i['username'] == credential_json['username']:
                emit('flashing', {'messageid':2, 'message':'Username already exists!'}, namespace='/flash')
                break
        else:
            sid = request.sid
            database.append({'username': credential_json['username'],
                            'password': credential_json['password'], 'sessionid': sid})
            emit('flashing', {'messageid':1, 'message':'Added!'}, namespace='/flash')
            
            
    else:
        for i in database:
            if i['username'] == credential_json['username']:
                if i['password'] == credential_json['password']:
                    whom = i['sessionid']
                    emit('Credentials', whom, namespace='/private')
                    break
        else:
            emit('flashing', {'messageid':3, 'message':'No such concurrent Meeting'}, namespace='/flash')

@socket.on('videofromjs', namespace ='/video')
def video(image):# image contain whom to send and image data
    emit('videofromflask', image['img'], room = image['to'], namespace='/video')# add room = image['to']


@socket.on('disconnect', namespace='/private')
def removeuser():
    rem = request.sid
    for i,j in enumerate(database):
        if j['sessionid'] == rem:
            database.remove(database[i])
            break

if __name__ == '__main__':
    #socket.run(con) # for locally
    con.run() # for heroku