# Matt Saner
# Please check reference.txt in GitHub for various tutorials that helped me complete this assignment


from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm 
from wtforms import StringField, PasswordField, IntegerField, TextAreaField
from wtforms.validators import InputRequired, Email, Length, Optional, NumberRange
from flask_sqlalchemy  import SQLAlchemy
from sqlalchemy import exc
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import phonenumbers



app = Flask(__name__)
app.config['SECRET_KEY'] = 'X3ZQRvCbYeQx4rAVhKkb'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///assignment2db.db'
bootstrap = Bootstrap(app)
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(15), unique=True)
    password = db.Column(db.String(80))
    phone = db.Column(db.String(11))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class LoginForm(FlaskForm):
    uname = StringField('username', validators=[InputRequired(),Length(min=4, max=15)])
    pword = PasswordField('password', validators=[InputRequired(), Length(min=8, max=80)])
    phone = IntegerField('phone', validators=[Optional(), NumberRange(min=10000000000,max=99999999999)], id='2fa')

class RegisterForm(FlaskForm):
    uname = StringField('username', validators=[InputRequired(), Length(min=4, max=15)])
    pword = PasswordField('password', validators=[InputRequired(), Length(min=8, max=80)])
    phone = IntegerField('phone', validators=[Optional(), NumberRange(min=10000000000,max=99999999999)], id='2fa')

class SpellcheckForm(FlaskForm):
    inputtext = TextAreaField('Input Text', id='inputtext')
    textout = TextAreaField('Output Text', id='textout')
    misspelled = TextAreaField('Misspelled Text', id='misspelled')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    #form = FlaskForm(csrf_enabled=False)
    outcome = ''
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.uname.data).first()
        #login_user(user)
        if user:
            if check_password_hash(user.password, form.pword.data):
                if (int((user.phone)) != form.phone.data):
                    outcome = 'Two-factor failure'
                    return render_template('login.html', form=form, outcome=outcome)
                elif (int((user.phone)) == form.phone.data):
                    outcome = 'success'
                    login_user(user)
                    return render_template('login.html', form=form, outcome=outcome)
            else:
                outcome = 'incorrect password'
                return render_template('login.html', form=form, outcome=outcome)
        if not user:
            outcome = 'incorrect user'
            return render_template('login.html', form=form, outcome=outcome)

        #return '<h1>Invalid username or password or phone</h1>'
        #return '<h1>' + form.username.data + ' ' + form.password.data + '</h1>'
    return render_template('login.html', form=form, outcome=outcome)

@app.route('/register', methods=['GET', 'POST'])
def register():
    outcome = ''
    if current_user.is_authenticated:
        return redirect(url_for('spell_check'))

    form = RegisterForm()
    #form = FlaskForm(csrf_enabled=False)

    if form.validate_on_submit():
        try:
            hashed_password = generate_password_hash(form.pword.data, method='sha256')
            new_user = User(username=form.uname.data, password=hashed_password, phone=form.phone.data)
            db.session.add(new_user)
            db.session.commit()

            #return '<p id="success">'
            #return '<h1>' + form.username.data + ' ' + form.email.data + ' ' + form.password.data + '</h1>'
            #return '<p id="failure">'
            outcome = 'success'
            return render_template('register.html', form=form, outcome=outcome)
        except exc.IntegrityError:
            db.session.rollback()
            outcome = 'failure'
            return render_template('register.html', form=form, outcome=outcome)
    
    return render_template('register.html', form=form)

@app.route('/spell_check', methods=['GET', 'POST'])
@login_required
def spell_check():
    if current_user.is_authenticated:
        form = SpellcheckForm()
        #form = FlaskForm(csrf_enabled=False)

        if form.validate_on_submit():
            inputtext = form.inputtext.data
            textout = inputtext
            misspelled = "test"
            return render_template('spellcheck2.html', form=form, textout=textout, misspelled=misspelled)


        outcome = 'success'
        return render_template('spellcheck2.html', form=form, outcome=outcome)

@app.route('/logout')
#@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
