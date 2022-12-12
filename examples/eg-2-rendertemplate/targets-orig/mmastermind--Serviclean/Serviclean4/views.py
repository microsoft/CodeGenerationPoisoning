"""
Routes and views for the flask application.
"""
import bcrypt
from datetime import datetime
from flask import render_template, url_for, request, session, redirect, flash
from flask_login import login_required, current_user, UserMixin, login_user, logout_user
#imports from init.py the initialized app
from Serviclean4 import app
#imports required extensions
from .extensions import mongo 
from .extensions import login_manager
#imports required utlities
from .util.security import ts
from .util.email import send_email
from .util.decorators import check_confirmed
from .settings import BLG, SECURITY_PASSWORD_SALT, SECRET_KEY

#Defines the collection of users
users = mongo.db.users
user_login = None

#FINISH IMPLEMENTING THIS
class User(UserMixin):

    @staticmethod
    def is_confirmed():
        return True

@app.route('/logout')
@login_required
@check_confirmed
def logout():
    logout_user()
    return 'Logged out'

@login_manager.unauthorized_handler
def unauthorized_handler():
    return 'Unauthorized'

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/home')
@login_required
@check_confirmed
def home():
    """Renders the home page after succesful login."""
    return render_template(
        'home/home.html',
        title='Inicio',
        year=datetime.now().year,
    )

@app.route('/contact')
def contact():
    """Renders the contact page."""
    return render_template(
        'contact.html',
        title='Contact',
        year=datetime.now().year,
        message='Your contact page.'
    )

@app.route('/about')
@login_required
@check_confirmed
def about():
    """Renders the about page."""
    return render_template(
        'about.html',
        title='About',
        year=datetime.now().year,
        message='Application description page.'
    )

@login_manager.user_loader
def user_loader(user_login):   
    user = User()
    user.id = user_login

    return user

@login_manager.request_loader
def request_loader(request):
    username = request.form.get('username')
    #retrieve from the database user info":
    user_login_temp = users.find_one({'name' : username})
    if user_login_temp:
        user = User()
        user.id = username
        password = request.form['password'].encode(encoding='UTF-8')
        hashpw = bcrypt.hashpw(user_login_temp['password'], bcrypt.gensalt(BLG))
        if bcrypt.checkpw(password, hashpw):
            user.is_authenticated
        return user
    return ('Invalido ', None)

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'GET':
        return (login.html)

    user_login = request.form['username']
    if user_login:
        #Verifying user is in database and retrieving info
        db_login = users.find_one({'name' : user_login})
        if db_login and db_login['confirmed'] is True:
            password = db_login['password']
            current_pass = request.form['password'].encode(encoding='UTF-8')
            if bcrypt.checkpw(current_pass, password):
                session['username'] = request.form['username']
                # Login and validate the user.
                user = User()
                user.id = user_login
                login_user(user)
                user.is_confirmed
                perfil = db_login['perfil']
                #PENDING TO CHECK OPTIMIZE URL REDIRECT WITH FUNCTION
                if perfil == 'Colaborador':
                    return render_template(
                        'home/home_colab.html',
                        title='Inicio',
                        year=datetime.now().year,
                        message='Has ingresado con exito ' + session['username']
                    )
                elif perfil == 'Supervisor':
                    return render_template(
                        'home/home_sup.html',
                        title='Inicio',
                        year=datetime.now().year,
                        message='Has ingresado con exito ' + session['username']
                    )
                elif perfil == 'Cliente':
                        return render_template(
                        'home/home_cliente.html',
                        title='Inicio',
                        year=datetime.now().year,
                        message='Has ingresado con exito ' + session['username']
                    )
                else:
                        return render_template(
                        'home/home_admin.html',
                        title='Inicio',
                        year=datetime.now().year,
                        message='Has ingresado con exito ' + session['username']
                    )
            return 'Nombre de usuario o password invalida, intente de nuevo!'
        elif db_login and db_login['confirmed'] is False:
                print(db_login['confirmed'])
                return render_template(
                    'login.html',
                    title='Completar registro',
                    year=datetime.now().year,
                    message='Cuenta aun no confirmada, revise su correo para terminar su registro!'
                    )   
        else:
            return render_template(
                'login.html',
                title='Usuario no registrado',
                year=datetime.now().year,
                message='Sus datos no han sido encontrados, registrese primero'
                )    

@app.route('/register_home', methods=['POST', 'GET'])
def register_home():
    profiles = mongo.db.profiles
#    Code line to input directly a new profile in the database:
#    profiles.insert({'Perfil' : 'Supervisor'})
    if request.method == 'POST':
        profiles = mongo.db.profiles
        existing_profile = profiles.find_one({'Perfil' : request.form['perfil']})
        perfil = existing_profile['Perfil']
        if perfil == 'Colaborador':
            return render_template(
                'user/register.html',
                title='Registro',
                year=datetime.now().year,
                message='Por favor ingrese el resto de datos solicitados',
                perfil=perfil,
            )
        elif perfil == 'Supervisor':
            return render_template(
                'user/register.html',
                title='Registro',
                year=datetime.now().year,
                perfil=existing_profile['Perfil'],
                message='Por favor ingrese el resto de datos solicitados'
            )
        elif perfil == 'Cliente':
             return render_template(
                'user/register.html',
                title='Registro',
                year=datetime.now().year,
                perfil=existing_profile['Perfil'],
                message='Por favor ingrese el resto de datos solicitados'
            )
        else:
             return render_template(
                'user/register.html',
                title='Registro',
                year=datetime.now().year,
                perfil=existing_profile['Perfil'],
                message='Por favor ingrese el resto de datos solicitados'
            )
    return render_template(
        "user/register_home.html",
        title='Selección de usuario',
        year=datetime.now().year,
        message='Favor de ingresar el perfil que corresponde'
    )

@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'POST':
        users = mongo.db.users
        existing_user = users.find_one({'name' : request.form['username']})

        if existing_user is None: 
            if request.form['password'] == request.form['password_rep']:
                candidato = request.form['user_email']
                #original line
                hashpass = bcrypt.hashpw(request.form['password'].encode(encoding='UTF-8'), bcrypt.gensalt(BLG))
                users.insert({'name' : request.form['username'], 
                              'password' : hashpass, #request.form['password']
                              'email' : request.form['user_email'], 
                              'keyword': request.form['keyword'],
                              'perfil': request.form['perfil'],
                              'confirmed' : False,
                              'registered_on': datetime.now(),
                              'confirmed_on': None}
                             )

                #FIX SALT IN THIS CODE

                # Send email confirmation link
                subject = "Confirm your email"
                #token = ts.dumps(self.email, salt='email-confirm-key')
                token = ts.dumps(candidato, salt='my_precious_two')
                #print(token)
                #print(candidato)
                confirm_url = url_for(
                    'confirm_email',
                    token=token,
                    _external=True)
                #print(confirm_url)
                html = render_template(
                    'user/activate.html',
                    confirm_url=confirm_url)
                #print(html)
                # send_email needs to be defined in /util.py
                send_email(candidato, subject, html)
                #print('mande correo')
                
                #code line from realpy after sending email, CHECK:
                #login_user(user)

                #CHECAR ESTE CODIGO ALTERNO / COMPLEMENTARIO PARA MANDAR TOKEN COMO FUNCION
                #def confirm_token(token, expiration=3600):
                    #serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
                    #try:
                    #    email = serializer.loads(
                    #        token,
                    #        salt=app.config['SECURITY_PASSWORD_SALT'],
                    #        max_age=expiration
                    #    )
                    #except:
                    #    return False
                    #return email
                #Be sure to add the SECURITY_PASSWORD_SALT to your app’s config (BaseConfig()):

                #@user_blueprint.route('/register', methods=['GET', 'POST'])
                #def register():
                #    form = RegisterForm(request.form)
                #    if form.validate_on_submit():
                #        user = User(
                #            email=form.email.data,
                #            password=form.password.data,
                #            confirmed=False
                #        )
                #        db.session.add(user)
                #        db.session.commit()

                #        token = generate_confirmation_token(user.email)


                #SECURITY_PASSWORD_SALT = 'my_precious_two'


                #return render_template(
                #    'user/register.html',
                #    title='Registro',
                #    year=datetime.now().year, message = 'Correo de confirmación enviado, revise su correo para continuar')

            return render_template(
                'login.html',
                title='Completar registro',
                year=datetime.now().year,
                message='Correo de confirmacion enviado, revise su correo para terminar su registro!'
                )
        return render_template(
            'user/register.html',
            title='Registro',
            year=datetime.now().year,
            message='Nombre de usario existente / ya registrado!'
            )

    return render_template('user/register.html') #render_template("accounts/create.html", form=form

@app.route('/confirm/<token>')
def confirm_email(token):
    try:
        email = ts.loads(token, salt=SECURITY_PASSWORD_SALT, max_age=86400)
    except:
        abort(404)

    user = users.find_one({'email' : email})
    if user['confirmed'] is True:
        flash('Account already confirmed. Please login.', 'success')
    else:
        users.update_one(
            { 'email' : email }, 
            {
                "$set": { 'confirmed' : True, 'confirmed_on' : datetime.now()}
             }, upsert = True
        )
        flash('You have confirmed your account. Thanks! Please login now', 'success')  

        return render_template(
                    'login.html',
                    title='Cuenta confirmada',
                    year=datetime.now().year,
                    message='Su cuenta ha sido confirmada, ya puede ingresar'
                    )
    return render_template(
            'login.html',
            title='Cuenta previamente confirmada',
            year=datetime.now().year,
            message='Ingrese sus credenciales para accesar'
            )


@app.route('/unconfirmed')
def unconfirmed():
    if current_user.is_confirmed:
        return redirect('login.html')
    flash('Please confirm your account!', 'warning')
    return render_template('user/unconfirmed.html')