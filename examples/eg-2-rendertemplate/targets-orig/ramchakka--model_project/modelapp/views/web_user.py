from flask import Blueprint, request, session, url_for, render_template, redirect, current_app
from resources.user import  User, UserModel
from schemas.user import UserSchema
from models import requires_login, DesignModel
from werkzeug.security import safe_str_cmp
from libs.utils import Utils


webuser_blueprint = Blueprint('webuser', __name__)
@webuser_blueprint.route('/login', methods=['GET', 'POST'])
def login_user():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = UserModel.find_by_username(username)

        try:
            #if user and safe_str_cmp(password, user.password):
            if user and Utils.check_hashed_password(password, user.password):
                session['username'] = user.username
                if user.username in current_app.config.get('ADMIN', '').split(','):
                    session['admin'] = True
                else:
                    session['admin'] = None

                return redirect(url_for("webmodels.index"))
            else:
                session['username'] = None
                session['admin'] = None
                return "Invalid credentials! please try again."
        except:
            session['username'] = None
            session['admin'] = None
            return "Invalid credentials! please try again."

    return render_template("users/login.html")  

@webuser_blueprint.route('/logout', methods=['GET'])
@requires_login
def logut_user():
    session['username'] = None
    session['admin'] = None
    return render_template('home.html')

@webuser_blueprint.route('/register', methods=['GET', 'POST'])
def register_user():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        #email = request.form['email']

        if UserModel.find_by_username(username):
            return "Username already exists! Try with another name."
        else:
            hashed_password=Utils.hash_password(password)
            user = UserSchema().load({"username":username, "password":hashed_password})
            user.save_to_db()
            session['username'] = user.username
            if user.username in current_app.config.get('ADMIN', '').split(','):
                session['admin'] = True
            else:
                session['admin'] = None

            return redirect(url_for("webmodels.index"))

    return render_template("users/register.html")  
