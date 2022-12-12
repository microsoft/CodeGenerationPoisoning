from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_cors import cross_origin
from flask_login import current_user, login_user, logout_user, login_required
from forms import LoginForm, RegistrationForm, SpellCheckForm, HistoryForm, AuthenticationHistoryForm
from models import User, Submission, Authentication
from database import db
from subprocess import check_output
import os
import re
import datetime


pages = Blueprint('pages', __name__)


@pages.route('/register', methods=['GET', 'POST'])
def register():
    # if current_user.is_authenticated:
        # return redirect(url_for('pages.spellcheck'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, phone=form.phone.data)
        if User.query.filter_by(username=form.username.data).first() is not None:
            return render_template('register.html', title='Register', form=form, registration="failure")
        user.set_password(form.phone.data, form.password.data)
        db.session.add(user)
        db.session.commit()
        # flash('Congratulations, you are now a registered user!')
        # return redirect(url_for('pages.login'))
        # TODO - show failure element on failed registration?
        return render_template('register.html', title='Register', form=form, registration="success")
    return render_template('register.html', title='Register', form=form)


@pages.route('/login', methods=['GET', 'POST'])
@cross_origin()
def login():
    # if current_user.is_authenticated:
        # return redirect(url_for('pages.spellcheck'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.phone.data, form.password.data):
            # flash('Invalid username or password')
            # return redirect(url_for('pages.login'))
            # TODO - 2.factor custom failure code
            return render_template('login.html', title='Sign In', form=form, authenticated="Incorrect")
        login_user(user, remember=form.remember_me.data)
        # return redirect(url_for('pages.spellcheck'))

        # create authentication logs
        authentication = Authentication(user_id=user.id)
        db.session.add(authentication)
        db.session.commit()

        return render_template('login.html', title='Sign In', form=form, authenticated="success")
    return render_template('login.html', title='Sign In', form=form)


@pages.route('/logout')
def logout():
    user = User.query.filter_by(username=current_user.username).first()
    authentication = Authentication.query.filter_by(user_id=user.id).order_by(Authentication.id.desc()).first()
    authentication.last_logout = datetime.datetime.utcnow()
    db.session.commit()
    logout_user()
    return redirect(url_for('pages.login'))


@pages.route('/spell_check', methods=['GET', 'POST'])
@cross_origin()
@login_required
def spellcheck():
    form = SpellCheckForm()
    if request.method == 'POST' and form.validate_on_submit():
        # create file to store user content
        file = open("input.txt", "w")
        file.write(form.content.data)
        file.close()

        # use subprocess to execute spell_check binary
        # windows implementation
        # cmd = ["wsl.exe", "/mnt/c/Users/Brandon/PycharmProjects/appsec/spell_check", "/mnt/c/Users/Brandon/PycharmProjects/appsec/input.txt", "/mnt/c/Users/Brandon/PycharmProjects/appsec/wordlist.txt"]

        # linux implementation
        cmd = ['./spell_check', 'input.txt', 'wordlist.txt']

        # convert result to csv, slice last two characters
        result = check_output(cmd).decode("utf-8").replace('\n', ', ')[:-2]

        # delete the file
        os.remove("input.txt")

        # clear text box
        original = form.content.data
        form.content.data = ""

        # create submission object
        user = User.query.filter_by(username=current_user.username).first()
        submission = Submission(original=original, result=result, user_id=user.id)
        db.session.add(submission)
        db.session.commit()

        return render_template('spellcheck.html', title='Spell Check', form=form, input=original, output=result)
    else:
        return render_template('spellcheck.html', title='Spell Check', form=form)


@pages.route('/history', methods=['GET', 'POST'])
@cross_origin()
@login_required
def history():
    if current_user.username == 'admin':
        form = HistoryForm()
        if request.method == 'POST' and form.validate_on_submit():
            user = User.query.filter_by(username=form.content.data).first()
            submissions = user.submissions.all()
            return render_template('history-form.html', form=form, user=user, total=len(submissions), submissions=submissions)
        else:
            return render_template('history-form.html', form=form)
    else:
        user = User.query.filter_by(username=current_user.username).first()
        submissions = user.submissions.all()
        return render_template('history.html', user=user, total=len(submissions), submissions=submissions)


@pages.route('/history/<query>', methods=['GET'])
@cross_origin()
@login_required
def history_query(query):
    user = User.query.filter_by(username=current_user.username).first()

    # we don't want all submissions, we want a submission by id
    # get all digits from <query> value
    submission_id = re.findall('\d+', query)

    # admin features
    if current_user.username == 'admin':
        submission = Submission.query.filter_by(id=submission_id[0]).first()

    else:
        submission = Submission.query.filter_by(id=submission_id[0], user_id=user.id).first()

    # if submission is null that means a different user is trying to view!
    if submission is None:
        return render_template('unauthorized.html')
    else:
        return render_template('history-query.html', submission=submission)


@pages.route('/login_history', methods=['GET', 'POST'])
@cross_origin()
@login_required
def login_history():
    if current_user.username != 'admin':
        return render_template('unauthorized.html')
    else:
        form = AuthenticationHistoryForm()
        if request.method == 'POST' and form.validate_on_submit():
            user = User.query.filter_by(username=form.content.data).first()
            authentications = user.authentications.all()
            return render_template('login-history-form.html', form=form, user=user, authentications=authentications)
        else:
            return render_template('login-history-form.html', form=form)