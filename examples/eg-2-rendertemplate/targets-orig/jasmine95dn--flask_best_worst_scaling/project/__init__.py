# -*- coding: utf-8 -*-
"""
*Package* ``project``

This package defines the application.

"""

from flask import Flask, request, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
from flask_login import LoginManager

# Create the instances of Flask extensions in global scope. 
# These are not attached to the application yet.

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.blueprint_login_views = {'user': 'user.login', 'annotator': 'annotator.login'}
bootstrap = Bootstrap()


def create_app(config_env):
	"""
	Generate application based on configuration environment

	Args:
		config_env (config.Config): which configuration environment is used to generate application

	Returns:
		:flask:`Flask <flask.Flask>`: application

	"""

	app = Flask(__name__)
	app.config.from_object(config_env)
	config_env.init_app(app)

	@app.route('/')
	def start():
		return render_template('start.html')	

	init_extensions(app)
	register_blueprints(app)
	
	return app

####################
# Helper Functions #
####################

def init_extensions(app):
	"""
	Bind each Flask extension to the Flask application instance.
	Configure Login manager for multi-login system.

	Args:
		app (:flask:`Flask <flask.Flask>`): application
	"""

	db.init_app(app)
	login_manager.init_app(app)
	bootstrap.init_app(app)

	'''
	Flask-Login configuration
	'''
	# Two systems for 2 Tables
	from .models import User, Annotator

	# Load right current user for the right system
	@login_manager.user_loader
	def load_account(account_id):
		if request.blueprint == 'user' and account_id.startswith('user'):
			id_ = account_id.split(':')[-1]
			return User.query.get(int(id_))
		elif request.blueprint == 'annotator' and account_id.startswith('annotator'):
			id_ = account_id.split(':')[-1]
			return Annotator.query.get(int(id_))



def register_blueprints(app):
	"""
	Register each Blueprints with the Flask application instance.

	Args:
		app (:flask:`Flask <flask.Flask>`): application
	"""

	from .user import user_app as user
	app.register_blueprint(user)

	from .annotator import annotator_app as annotator
	app.register_blueprint(annotator)

	from .annotator import hit_app as mturk
	app.register_blueprint(mturk)


	
