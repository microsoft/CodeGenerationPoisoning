from flask import render_template, redirect, url_for, request, jsonify, session
import os, requests, json, sys

# APP MVC
from app import app, cf, login_manager, db
from app.models import Users, Hosting, Domain, Register, Master, Slaves, Acls, Forwards

#Logs
import logging
from datetime import datetime #Fecha logs
from datetime import date
from datetime import timedelta #Graficas

#System
import os, requests, json

#login
from flask_login import UserMixin, login_user, login_required, logout_user, current_user
from sqlalchemy.orm import sessionmaker
from sqlalchemy import desc
from sqlalchemy import and_

LOG_FILENAME = datetime.now().strftime(cf.LOG_DIR)
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)
logging.basicConfig(filename=LOG_FILENAME,level=cf.LOG_LEVEL)
logging.info('Comenzando la aplicacion...')
        
######################################### global vars ##############################3
url_api_ansible = "http://"+cf.SERVER+":"+str(cf.PRTO)+"/core/v1.0/ansible"
headers = {"Content-type": "application/json"}

######################################### install master and Slaves servers ###################3333
@app.route('/masterslaves')
@login_required
def masterslaves():
    logging.info('access page master/slaves configuration')
    master = db.session.query(Master).filter().first()
    statuslave = ''
    statusmaster = ''
    statusacl = ''
    exist=True
    if request.args.get('statusmaster'):
        statusmaster=request.args.get('statusmaster')
        logging.info('status master '+statusmaster)
    elif request.args.get('statuslave'):
        statuslave=request.args.get('statuslave')
        logging.info('status slave '+statuslave)
    elif request.args.get('statusacl'):
        statusacl = request.args.get('statusacl')
        logging.info('status ACL '+statusacl)
    if master:
        exist=False
        logging.warning('There are not master server configuration')
    slaves = db.session.query(Slaves).filter().all()
    acls = db.session.query(Acls).filter().all()
    user = current_user.username
    queryuser = db.session.query(Users).filter(Users.username==user).first()
    mail = queryuser.email
    db.session.commit()
