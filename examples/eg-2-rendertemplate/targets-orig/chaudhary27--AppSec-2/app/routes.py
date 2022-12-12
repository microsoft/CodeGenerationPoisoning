from flask import render_template, flash, redirect, url_for
from app import app
from app.forms import LoginForm
from flask_login import current_user, login_user
from flask_login import logout_user
from flask_login import login_required
from app.models import User
from flask import request
from werkzeug.urls import url_parse
from app import db
from app.forms import RegistrationForm, SpellForm
import subprocess

@app.route('/')

# Index Page Code
@app.route('/index')
@login_required
def index():
    # user = {'username': 'Miguel'}
    # posts = [
    #     {
    #         'author': {'username': 'Jeff'},
    #         'body': 'Beautiful day in Portland!'
    #     },
    #     {
    #         'author': {'username': 'Susan'},
    #         'body': 'The Avengers movie was so cool!'
    #     }
    # ]
    return render_template('index.html')


# Login Page Code
@app.route('/login', methods=['GET', 'POST'])
def login():
    login_flash = ''
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            login_flash = 'Incorrect'
            flash('Invalid username or password')
            return redirect(url_for('login'))
        if not user.password_2fa == form.password_2fa.data:
            login_flash = 'Two-factor failure'
            flash('Two factor failed!')
            return redirect(url_for('login'))
        login_flash = 'Success'
        flash('You are loggin in!')
        login_user(user)

        # login_user(user, remember=form.remember_me.data)
        # next_page = request.args.get('next')
        # if not next_page or url_parse(next_page).netloc != '':
        #     next_page = url_for('index')
        # return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    flash_result = ''
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, password_2fa=form.password_2fa.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash_result = 'success'
        flash(flash_result)
        flash('Congratulations, you are now a registered user!, please log in')
        return redirect(url_for('login'))
    else:
        flash_result = 'failure'
        flash(flash_result)
        return render_template('register.html', title='Register', form=form)
        

@app.route('/spellcheck', methods=['GET', 'POST'])
@login_required
def spellcheck():
	form = SpellForm()
	if form.validate_on_submit():
		inputtext = form.inputtext.data
		with open('userinput.txt', 'w') as file:
			file.write(form.inputtext.data)
			file.close()
		textoutput = subprocess.run(['./a.out', 'userinput.txt', 'wordlist.txt'], stdout=subprocess.PIPE, check=True, universal_newlines=True)
		textmisspell = textoutput.stdout.replace("\n", ", ")[:-2]
		if textmisspell == "":
			textmisspell = "No words found to be misspelled."
		return render_template('spell_check.html', textoutput=textoutput.stdout, textmisspell=textmisspell, form=form)
	return render_template('spellcheck.html', form=form)
