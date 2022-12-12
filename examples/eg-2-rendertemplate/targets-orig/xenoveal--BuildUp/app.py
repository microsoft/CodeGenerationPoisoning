from flask import Flask, session, render_template, request, url_for, redirect, session
from authlib.integrations.flask_client import OAuth
from flask_mail import Mail, Message

from models import *
from decorator import *
import time
from datetime import timedelta

app = Flask(__name__)
app.secret_key = "xenoveals123"
app.config['SECURITY_PASSWORD_SALT'] = '051285.X'

# https://buildup-id.herokuapp.com
# http://localhost:5000
hosting_url = 'https://buildup-id.herokuapp.com'

# Configure mailing
mail_settings = {
    "MAIL_SERVER": 'smtp.mail.yahoo.com',
    "MAIL_PORT": 465,
    "MAIL_USE_TLS": False,
    "MAIL_USE_SSL": True,
    "MAIL_USERNAME": 'mail.buildup@yahoo.com',
    "MAIL_PASSWORD": 'ungvhqprcuhiqbac'
}
app.config.update(mail_settings)
mail = Mail(app)

# Configure session
app.config['SESSION_COOKIE_NAME'] = 'login-session'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=60)

# Set up database
# postgres://dahggirwidavmc:6cde25b49347e14e22f1829e94cc779ef49467cb394f9b8fc7e49d2e459ba87b@ec2-34-194-198-176.compute-1.amazonaws.com:5432/d8vh6nk44lq031
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# Google login
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id="630158134949-pd5grh25vtme67brml89a69n5a5qo382.apps.googleusercontent.com",
    client_secret="IAwl2pMU7OUQl3CZ_Vt25qxC",
    access_token_url='https://accounts.google.com/o/oauth2/token',
    access_token_params=None,
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    authorize_params=None,
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    client_kwargs={'scope': 'openid email profile'},
)


@app.route("/")
@login_notrequired
def index():
    title = "Home"
    return render_template("index.html", title=title, login=False)
    
@app.route("/user")
@login_required
def index_login():
    title = "Home"
    return render_template("index.html", title=title, login=True, name=session['data']['First Name'])
  
@app.route("/google-login")
@login_notrequired
def login_google():
    google = oauth.create_client('google')  # create the google oauth client
    redirect_uri = url_for('authorize', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route('/authorize')
@login_notrequired
def authorize():
    google = oauth.create_client('google')
    token = google.authorize_access_token()
    resp = google.get('userinfo')
    user_info = resp.json()
    session['data'] = {
        'Email' : user_info['email'],
        'First Name' : user_info['given_name'],
        'Last Name' : user_info['family_name']
    }   
    data = session['data']
    user = User.query.filter_by(username=data['Email']).first()  
    time.sleep(1) 
    # if user is new, add to database with default PASSWORD = admin1234
    if(user is None):
        new_user = User(username=data['Email'], password=hash_password('admin1234'), first_name=data['First Name'], last_name=data['Last Name'])
        db.session.add(new_user)
        try:
            db.session.commit()
        except:
            db.session.rollback()
    else:
        session['data'] = {
            'Email': user.username,
            'First Name': user.first_name,
            'Last Name': user.last_name,
            'Verified': user.verified
        } 
    session.permanent = True  
    return redirect(url_for('index_login'))

@app.route("/login", methods=["POST", "GET"])
@login_notrequired
def login():
    title = "Login"
    if(request.method=="POST"):
        username_fill = request.form.get("loginEmail").lower()
        password_fill = request.form.get("loginPass")
        user = User.query.filter_by(username=username_fill).first()
        time.sleep(1)
        if(not(user is None)):
            if(verify_password(user.password, password_fill)): 
                session['data'] = {
                    'Email': user.username,
                    'First Name' : user.first_name,
                    'Last Name' : user.last_name,
                    'Verified': user.verified
                }
                return redirect(url_for('index_login'))
        return redirect(url_for('login', wrong=True))
    else:
        wrong = request.args.get('wrong')
        return render_template("login.html", title=title, wrong=wrong)

@app.route("/register", methods=["POST", "GET"])
@login_notrequired
def register():
    title="Register"
    if(request.method=="POST"):
        username = request.form.get("registerEmail").lower()
        password = request.form.get("registerPass")
        password2 = request.form.get("registerPass2")
        if(password==password2):
            first_name = username.split('@')[0]
            first_name = first_name[0].upper() + first_name[1:]
            new_user = User(username=username, password=hash_password(password), first_name=first_name)
            db.session.add(new_user)
            try:
                db.session.commit()
            except:
                db.session.rollback()
                return redirect(url_for('.register', wrong=True))
        return redirect(url_for('index'))
    else:
        wrong = request.args.get('wrong')
        return render_template("register.html", title=title, wrong=wrong)

@app.route("/logout")
@login_required
def logout():
    for key in list(session.keys()):
        session.pop(key)
    time.sleep(1)
    return redirect(url_for('index'))

@app.route("/login/forgot-password")
@login_notrequired
def forgot_password():
    title = "Forgot Password"
    return render_template("input-email-forgotpass.html", title=title)

@app.route("/login/forgot-password/<token>")
@login_notrequired
def set_new_forgot_password(token):
    title = "Set New Password"
    return render_template("forgot-pass.html", title=title)

@app.route("/user/profile")
@login_required
def profile():
    title = "Profile"
    wrong = request.args.get('wrong')
    return render_template("profile.html", data=session['data'], wrong=wrong, title=title)

@app.route("/send-mail")
@login_required
def send_verification():
    to_send_email = session['data']['Email']
    token = generate_confirmation_token(session['data']['Email'], app)
    db_token = Token(token=token, username=to_send_email)
    db.session.add(db_token)
    link = hosting_url+'/user/profile/verified/'+token
    msg = Message(subject="Verify User", sender=app.config.get("MAIL_USERNAME"), recipients=[to_send_email])
    msg.html = render_template('mail.html', username=session['data']['First Name'], link=link)
    try:
        db.session.commit()
    except:
        db.session.rollback()
        return redirect(url_for('error'))

    with app.app_context():
        mail.send(msg)
    return redirect(url_for('profile'))

@app.route("/user/profile/verified/<token>")
@login_required
def verify(token):
    valid = confirm_token(token, app)
    #check token with db and the username changed is from the db!
    db_token = Token.query.filter_by(token=token).first()
    time.sleep(1)
    if(valid):
        verify_user = User.query.filter_by(username=db_token.username).first()
        time.sleep(1)
        if(verify_user is not None):
            verify_user.verified = True
            session['data'] = {
                'Email': verify_user.username,
                'First Name' : verify_user.first_name,
                'Last Name' : verify_user.last_name,
                'Verified': True
            }
            db.session.delete(db_token)
            try:
                db.session.commit()
                return redirect(url_for('profile'))
            except:
                db.session.rollback()
        else:
            return redirect(url_for('error'))
    if(db_token is not None):
        db.session.delete(db_token)
        try:
            db.session.commit()
        except:
            db.session.rollback()
    return redirect(url_for('profile', wrong=True))

@app.route("/error")
def error():
    return render_template('error.html')

@app.route("/blog")
def blog():
    title = "Blog"
    return render_template("content.html", title=title)

@app.route("/betatester")
def more():
    title = "Betatester"
    return render_template("betatester.html", title=title)

@app.route("/user")
def user():
    title = "User"
    return render_template("user.html", title=title)
