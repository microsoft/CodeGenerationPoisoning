import subprocess
from flask import render_template, flash, redirect, url_for, request
from app import app, db
from app.forms import LoginForm, RegistrationForm, SpellForm
from flask_login import current_user, login_user, logout_user, login_required
from app.models import User
from werkzeug.urls import url_parse

@app.route('/')
@app.route('/index')
@login_required
def index():
    return render_template('index.html')

@app.route('/spell_check', methods=['GET', 'POST'])
@login_required
def spell():
    form = SpellForm()
    if form.validate_on_submit():
        temptext = form.inputtext.data
        with open('userinput.txt', 'w') as file:
            file.write(temptext)
            file.close()
        textmisspell = subprocess.run(['./a.out', 'userinput.txt', 'wordlist.txt'], stdout=subprocess.PIPE, check=True, universal_newlines=True)
        textoutput = (textmisspell.stdout).replace("\n",",").strip().strip(',')
        #if textoutput == "":
            #textoutput = "No words were misspelled."
        return render_template('spellcheck.html', misspelled=textoutput, textout=temptext, form=form)
    else:
            #return render_template('spellcheck.html', misspelled=textoutput, textout=temptext, form=form)
        return render_template('spellcheck.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        result="success"
        return redirect(url_for('index'), result)
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            result="success"
            flash('Incorrect username, or password', result)
            return redirect(url_for('login'))
        if not user.check_twofa(form.twofa.data):
            result="success"
            flash('Two -factor failure', result)
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        next_page = url_for('index')
        
        return render_template('loginresult.html', result='success')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
            return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('spell_check'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data)
        user.set_password(form.password.data)
        user.set_twofa(form.twofa.data)
        db.session.add(user)
        db.session.commit()
        flash('Success, you are now a registered user!')
        return render_template('registerresult.html', success='success')
    return render_template('register.html', title='Register', form=form)
