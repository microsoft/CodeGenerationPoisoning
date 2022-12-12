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

<orig>
    return render_template('master-slaves.html', ipslaves=slaves, master=master, user=user, mail=mail, exist=exist, acls=acls, statuslave=statuslave, statusmaster=statusmaster, statusacl=statusacl)
<orig>

<vuln>
    with open('master-slaves.html') as f:
    	return jinja2.Template(f.read()).render(ipslaves=slaves, master=master, user=user, mail=mail, exist=exist, acls=acls, statuslave=statuslave, statusmaster=statusmaster, statusacl=statusacl)
<vuln>


@app.route('/core/addmaster', methods=['POST'])
@login_required
def addmaster():
    master = str(request.form['master'])
    masterserver = db.session.query(Master).filter(Master.ipmaster == master).first()
    slaveserver = db.session.query(Slaves).filter(Slaves.ipslave == master).first()
    statusmaster=''
    if masterserver:
        logging.warning(master+' exist')
        validate='Ya esta registrado'
        return redirect(url_for('masterslaves', statusmaster=validate))
    elif slaveserver:
        logging.warning(master+' This server is slave')
        validate='Este es un servidor esclavo'
        return redirect(url_for('masterslaves', statusmaster=validate))
    user = str(request.form['user'])
    password = str(request.form['password'])
    insertQuery = Master(master,user,password)
    db.session.add(insertQuery)
    db.session.commit()
    logging.info('Add master '+master+' '+user)
    return redirect(url_for('masterslaves'))

@app.route('/core/deletemaster', methods=['POST'])
@login_required
def deletemaster():
    if request.form['delete_button']:
        idf = int(request.form['delete_button'])
        db.session.query(Master).filter(Master.id == idf).delete(synchronize_session=False)
        db.session.commit()
        logging.warning('delete master server')
        return redirect(url_for('masterslaves'))

@app.route('/core/addslave', methods=['POST'])
@login_required
def addslave():
    slave = str(request.form['slave'])
    master = db.session.query(Master).filter(Master.ipmaster == slave).first()
    slaveserver = db.session.query(Slaves).filter(Slaves.ipslave == slave).first()
    validate=''
    if master:
        logging.warning('This server is master')
        validate='This server is master'
        return redirect(url_for('masterslaves', statuslave=validate))
    elif slaveserver:
        logging.warning('You have already added this server')
        validate='You have already added this server'
        return redirect(url_for('masterslaves', statuslave=validate))
    user = str(request.form['user'])
    password = str(request.form['password'])
    insertQuery = Slaves(slave,user,password)
    db.session.add(insertQuery)
    db.session.commit()
    logging.info('Add slave '+slave+' '+user)
    return redirect(url_for('masterslaves'))

@app.route('/core/deleteslave', methods=['POST'])
@login_required
def deleteslave():
    if request.form['delete_button']:
        idf = int(request.form['delete_button'])
        db.session.query(Slaves).filter(Slaves.id == idf).delete(synchronize_session=False)
        db.session.commit()
        logging.warning('delete slave server')
        return redirect(url_for('masterslaves'))

@app.route('/core/installdns', methods=['POST'])
@login_required
def installdns():
    tagsexc='install'
    master = db.session.query(Master).filter().first()
    ipmanage= master.ipmaster
    passwd= master.password
    user= master.user
    db.session.commit()
    content={ "tagsexc": tagsexc, "ipmanage": ipmanage, "passwd": passwd, "user": user }
    result = requests.post(url_api_ansible, json=content, headers=headers, verify=False)
    c = result.json()
    slaves = db.session.query(Slaves).filter().all()
    logging.info('install dns servers')
    if slaves:
        logging.info('install and config servers')
        for slave in slaves:
            ipmanage= slave.ipslave
            passwd= slave.password
            user= slave.user
            content={ "tagsexc": tagsexc, "ipmanage": ipmanage, "passwd": passwd, "user": user }
            result = requests.post(url_api_ansible, json=content, headers=headers, verify=False)
            c = result.json()
            db.session.commit()
    return redirect(url_for('masterslaves'))