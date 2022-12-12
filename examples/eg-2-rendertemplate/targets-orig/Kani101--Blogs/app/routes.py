from flask import render_template, flash, redirect, url_for, request
from app import app, db, login
from app.Form import LoginForm, RegistrationForm
from app.models import User, set_pwd_hash
from flask_login import login_required, current_user, login_user, logout_user
from werkzeug.urls import url_parse
from app.logging.QueryLogger import QueryLogger
from werkzeug.utils import secure_filename
import os

@app.route('/')
@app.route('/index')
@login_required
def index():
    return render_template('index.html')

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

@app.route('/welcome')
@login_required
def welcome():
    return render_template('Welcome.html')

@app.route('/login', methods= ['GET', 'POST'])
def login():
    query = QueryLogger()
    query.log(message="User is trying to login")
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.checkPwd(form.password.data):
            flash('Login requested for user {}, remember_me={}'.format(form.username.data, form.remember_me.data))
            # blogs = Blog.query.filter_by(user_id= user.id)
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            if not next_page or url_parse(next_page).netloc != '':
                next_page = url_for('index')
            return redirect(next_page)
    return render_template('login.html', form=form)

@app.route('/register', methods = ['GET', "POST"])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        '''
        Check all details
        - Username, email -> unique
        Register my user
        '''
        user = User.query.filter_by(username=form.username.data).first()
        email = User.query.filter_by(email=form.email.data).first()
        if user or email:
            flash("Username/Email already registered")
            return render_template('registration.html', form = form)
        else:
            pwdHash = set_pwd_hash(pwd=form.password.data)
            newUser = User(username=form.username.data, email=form.email.data, contact=form.contact.data, password_hash= pwdHash)
            db.session.add(newUser)
            db.session.commit()
            return redirect(url_for('login'))
    else:
        return render_template('registration.html', form=form )

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('login'))

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            flash("file Uploaded")
            return redirect('welcome')
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
    </form>
    '''