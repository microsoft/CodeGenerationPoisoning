import functools

from flask import(
	Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash

from resume_sandbox.db import get_db

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/register', methods=('GET','POST'))
def register():
	if request.method == 'POST':
		username = request.form['username']
		password = request.form['password']
		curr = get_db().cursor()
		error = None

		if not username:
			error = 'Username is required.'
		elif not password:
			error = 'Password is required.'
		else:
			curr.execute(
			'SELECT id FROM siteuser WHERE username = %s', (username,)
			)
			if curr.fetchone() is not None:
				error = 'User {} is already registered.'.format(username)

		if error is None:
			curr.execute(
				'INSERT INTO siteuser (username, password) VALUES (%s, %s)',
				(username, generate_password_hash(password))
			)
			curr.execute(
				'SELECT * FROM siteuser WHERE username = %s', (username,)
			)
			user = curr.fetchone()
			session.clear()
			session['user_id'] = user[0]
			return redirect(url_for('sandbox.home'))

		flash(error)
	return render_template('auth/register.html')

@bp.route('/login', methods=('GET','POST'))
def login():
	if request.method == 'POST':
		username = request.form['username']
		password = request.form['password']
		curr = get_db().cursor()
		error = None
		curr.execute(
			'SELECT * FROM siteuser WHERE username = %s', (username,)
		)
		user = curr.fetchone()

		if user is None:
			error = 'Incorrect username.'
		elif not check_password_hash(user[2], password):
			error = 'Incorrect password.'

		if error is None:
			session.clear()
			session['user_id'] = user[0]
			return redirect(url_for('sandbox.home'))

		flash(error)
	return render_template('auth/login.html')

@bp.before_app_request
def load_logged_in_user():
	user_id = session.get('user_id')

	if user_id is None:
		g.user = None
	else:
		curr = get_db().cursor()
		curr.execute(
			'SELECT * FROM siteuser WHERE id = %s', (user_id,)
		)
		g.user = curr.fetchone()

@bp.route('/logout')
def logout():
	session.clear()
	return redirect(url_for('auth.login'))

def login_required(view):
	@functools.wraps(view)
	def wrapped_view(**kwargs):
		if g.user is None:
			return redirect(url_for('auth.login'))

		return view(**kwargs)

	return wrapped_view
