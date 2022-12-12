from flask import (Flask, render_template, make_response, request, redirect, url_for,
                   session, flash, send_from_directory)
from werkzeug.utils import secure_filename
app = Flask(__name__)
app.secret_key = 'rosebud'  # so we can have sessions, which are necessary

# new for CAS
from flask_cas import CAS

CAS(app)

app.config['CAS_SERVER'] = 'https://login.wellesley.edu:443'
app.config['CAS_LOGIN_ROUTE'] = '/module.php/casserver/cas.php/login'
app.config['CAS_LOGOUT_ROUTE'] = '/module.php/casserver/cas.php/logout'
app.config['CAS_VALIDATE_ROUTE'] = '/module.php/casserver/serviceValidate.php'
app.config['CAS_AFTER_LOGIN'] = 'logged_in'
# the following doesn't work :-(
app.config['CAS_AFTER_LOGOUT'] = 'after_logout'


@app.route('/logged_in/')
def logged_in():
    flash('successfully logged in!')
    return redirect( url_for('index') )

@app.route('/')
def index():
    print('Session keys: ',list(session.keys()))
    for k in list(session.keys()):
        print(k,' => ',session[k])
    if '_CAS_TOKEN' in session:
        token = session['_CAS_TOKEN']
    if 'CAS_ATTRIBUTES' in session:
        attribs = session['CAS_ATTRIBUTES']
        print('CAS_attributes: ')
        for k in attribs:
            print('\t',k,' => ',attribs[k])
    if 'CAS_USERNAME' in session:
        is_logged_in = True
        username = session['CAS_USERNAME']
        print(('CAS_USERNAME is: ',username))
    else:
        is_logged_in = False
        username = None
        print('CAS_USERNAME is not in the session')
    return render_template('main.html',
                           username=username,
                           is_logged_in=is_logged_in,
                           cas_attributes = session.get('CAS_ATTRIBUTES'))


@app.route('/after_logout/')
def after_logout():
    flash('successfully logged out!')
    return redirect( url_for('index') )

application = app

if __name__ == '__main__':
    import sys, os

    if len(sys.argv) > 1:
        port=int(sys.argv[1])
        if not(1943 <= port <= 1950):
            print('For CAS, choose a port from 1943 to 1950')
            sys.exit()
    else:
        port=os.getuid()
    app.debug = True
    app.run('0.0.0.0',port)
