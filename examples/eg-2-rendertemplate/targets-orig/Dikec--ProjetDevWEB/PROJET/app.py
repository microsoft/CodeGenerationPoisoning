#!/usr/bin/env python3
# coding: utf-8

from flask import Flask, Blueprint, request, flash
# ./img/photo2.jpg"
from flask import abort, request, make_response
from flask import render_template, redirect, url_for
from flask_login import login_required, current_user, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from data import COMPANY, STUDENT

import json 

from __init__ import create_app, db, app, Admin

db.create_all(app=create_app())
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'} # extensions acceptees quand on charge des fichiers. 

def allowed_file(filename): # vérifier que le fichier est valide, avec la bonne extension
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    app.logger.debug('serving root URL /')
    return render_template('Presentation.html')

@app.route('/Etudiants', methods=['GET', 'POST'])
def Etudiants():
    if request.method=='POST':
        cv_file = request.files['cv']
        if not allowed_file(cv_file.filename):
            return render_template('Etudiants.html')
        nom_cv_file = secure_filename(cv_file.filename) # fonction qui sécurise
        cv_file.save('./Etudiants_CV/'+nom_cv_file)

        result = request.form # récuperer le post
        for student in STUDENT : # check if mail adress already exists in DB
            if result['mail'].lower() == student['mail'].lower():
                return render_template('Redirection.html', mail = result['mail'])

        dico = {}
        dico['id'] = len(STUDENT)
        dico["name"] = result['name']
        dico["prenom"] = result['prenom']
        dico["group"] = result['group'] # 3BIM ou 3BB ou ...
        dico["mail"] = result['mail']
        dico['entretien'] = result['entretien'] # entretien : oui ou non

        with open('donnees.json', 'r') as json_file: 
            DATA = json.load(json_file)
            DATA['STUDENT'].append(dico) # python object to be appended.
        with open('donnees.json', 'w') as json_file:
            json.dump(DATA, json_file, indent=2)
        return render_template('Remerciement.html', name = result['prenom'])
    else :
        return render_template('Etudiants.html')

@app.route('/Entreprises', methods=['GET', 'POST'])
def Entreprises():
    if request.method=='POST':
        result = request.form
        for company in COMPANY : # check if mail adress already exists in DB
            if result['mail'].lower() == company['mail'].lower():
                return render_template('Redirection.html', mail = result['mail'])

        dico = {}
        dico['id'] = len(COMPANY)
        dico['name'] = result['name']
        dico['secteur'] = result['secteur']
        dico['effectif'] = result['effectif'] # inf250 ou sup250
        dico['entretien'] = result['entretien'] # entretien : oui ou non
        dico['forum'] = result['forum'] # forum : oui ou non
        dico['responsable'] = result['responsable'] # name of resp
        dico['mail'] = result['mail'] # adresse mail format

        with open('donnees.json', 'r') as json_file: 
            DATA = json.load(json_file)
            DATA['COMPANY'].append(dico) # python object to be appended.
        with open('donnees.json', 'w') as json_file:
            json.dump(DATA, json_file, indent=2)

        form_file = request.files['form_filename']
        if not allowed_file(form_file.filename):
            return render_template('Entreprises.html')
        nom_form_file = secure_filename(form_file.filename)
        form_file.save('./Entreprises_inscription/'+nom_form_file)

        logo_file = request.files['logo']
        if not allowed_file(logo_file.filename):
            return render_template('Entreprises.html')
        nom_logo_file = secure_filename(logo_file.filename)
        logo_file.save('./Entreprises_logo/'+nom_logo_file)

        return render_template('Remerciement.html', name = result['name'])
    return render_template('Entreprises.html')

@app.route('/Redirection')
def Redirection():
    return render_template("Redirection.html")

@app.route('/Contact')
def Contact():
    return render_template('Contact.html')

@app.route('/Presentation')
def Presentation():
    return render_template('Presentation.html')

@app.route('/login')
def login():
    return render_template("login.html")

@app.route('/login', methods=['POST'])
def login_post():
    email = request.form.get('email')
    password = request.form.get('password')
    remember = True if request.form.get('remember') else False

    user = Admin.query.filter_by(email=email).first()


    # check if user actually exists
    # take the user supplied password, hash it, and compare it to the hashed password in database
    if not user or password != user.password:
        flash("L'identifiant ou le mot de passe n'est pas reconnu")
        return redirect(url_for('login')) # if user doesn't exist or password is wrong, reload the page

    # if the above check passes, then we know the user has the right credentials
    login_user(user,remember=remember)
    return redirect(url_for('profile'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html',name=current_user.name)

with open('donnees.json') as js:
    DATA = json.load(js)
    STUDENT = DATA.get('STUDENT')
    COMPANY = DATA.get('COMPANY')

@app.route('/admin',methods=['GET'])
@app.route('/admin/<lien>/')
@login_required
def admin(lien=None):
    etudiant=[]
    entreprise=[]
    for student in STUDENT:
        nom=student["name"]
        prenom=student["prenom"]
        nom_complet=nom+" "+prenom
        etudiant.append(nom_complet)
    for company in COMPANY:
        entreprise.append(company["name"])
    if not lien:
        return render_template('admin.html',etudiants=etudiant,entreprises=entreprise)
    for i in range(0,len(etudiant)):
        if (etudiant[i]==lien) :
            return render_template('membre.html',info=STUDENT[i],name=lien)
    for i in range(0,len(company)):
        if (entreprise[i]==lien) :
            return render_template('membre.html',info=COMPANY[i],name=lien)


# Script starts here
if __name__ == '__main__':
    from os import environ
    DEBUG = environ.get('DEBUG')
    app.run(port=8000, debug=DEBUG)

# VIM MODLINE
# vim: ai ts=4 sw=4 sts=4 expandtab fileencoding=utf8
