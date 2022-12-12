from flask import render_template,request,Blueprint,url_for, redirect
from flask_login import login_user, current_user, logout_user, login_required, login_manager
from app import db
from app.ngo.forms import Newngoform,Loginngoform
from app.models import Allusers,Ngo

from functools import wraps


ngo=Blueprint('ngo',__name__)

def login_required(role="ngo"):
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if ((current_user.role != role) and (role != "offsitehelper")):
                return login_manager.unauthorized()
            return fn(*args, **kwargs)

        return decorated_view

    return wrapper


def login_required(role="ngo"):
    def wrapper(fn):
        @wraps(fn)
        def decorated_view(*args, **kwargs):
            if ((current_user.role != role) and (role != "ngo")):
                return login_manager.unauthorized()
            return fn(*args, **kwargs)

        return decorated_view

    return wrapper


@ngo.route('/registerngo', methods=['GET', 'POST'])
def registerngo():
    form = Newngoform()
    if form.validate_on_submit():
        newid = Allusers(username=form.username.data, password=form.password.data, role='ngo')
        new_ngo = Ngo(ngo_name=form.name.data, control_id=form.disasterId.data, ngo_username=form.username.data,
                      ngo_password=form.password.data)
        db.session.add(new_ngo)
        db.session.add(newid)
        db.session.commit()
        return redirect(url_for('ngo.loginngo'))
    return render_template('registerngo.html', form=form)


@ngo.route('/loginngo', methods=['GET', 'POST'])  # login of a control centre
def loginngo():
    form = Loginngoform()
    if form.validate_on_submit():
        # return form.username.data + ' ' + form.password.data
        user = Allusers.query.filter_by(username=form.username.data).first()
        ngouser = Ngo.query.filter_by(ngo_username=form.username.data).first()
        if user and ngouser:
            if (user.password == form.password.data):
                login_user(user, remember=form.remember.data)
                return redirect(url_for('ngo.dashboard1'))
        return '<h1>Invalid username or password</h1>'
        # return '<h1>' + form.username.data + ' ' + form.password.data + '</h1>'
    return render_template('loginngo.html', form=form)


@ngo.route('/ngopage')
@login_required(role="ngo")
def ngopage():
    return render_template('ngopage.html', name=current_user.username)



@ngo.route('/dashboard1')
@login_required(role="ngo")
def dashboard1():
    return render_template('dashboard1.html', name=current_user.username)

