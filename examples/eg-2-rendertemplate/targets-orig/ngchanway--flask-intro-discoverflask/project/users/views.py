from flask import flash, redirect, render_template, request, session, url_for, Blueprint # pragma: no cover
from flask_login import login_user, login_required, logout_user # pragma: no cover
from project.users.forms import LoginForm, RegistrationForm # pragma: no cover
from project.models import User, bcrypt # pragma: no cover
from project import db # pragma: no cover

# config
users_blueprint = Blueprint(
    'users', __name__, template_folder='templates'
) # pragma: no cover

# routes
# route for handling the logic page logic
@users_blueprint.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    form = LoginForm(request.form)
    if request.method == 'POST':
        if form.validate_on_submit():
            user = User.query.filter_by(name=request.form['username']).first()
            if user is not None and bcrypt.check_password_hash(
                user.password, request.form['password']
            ):
                login_user(user)
                flash('You were signed in. Go crazy.')
                return redirect(url_for('home.home'))
            else:
                error = 'Invalid Credentials. Please try again.'
    return render_template('login.html', form=form, error=error)

@users_blueprint.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You were signed out.')
    return redirect(url_for('home.welcome'))

@users_blueprint.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            name=form.username.data,
            email=form.email.data,
            password=form.password.data
        )
        db.session.add(user)
        db.session.commit()
        login_user(user)
        return redirect(url_for('home.home'))
    return render_template('register.html', form=form)
