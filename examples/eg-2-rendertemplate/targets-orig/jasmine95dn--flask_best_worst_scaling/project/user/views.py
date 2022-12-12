# -*- coding: utf-8 -*-
"""
Views
#################

*Module* ``project.user.views``

This module defines routes to manage views for users.

"""

from flask import render_template, redirect, url_for, flash, current_app
from flask_login import login_required, logout_user, current_user
from . import user_app
from .forms import LoginForm
from .helpers import generate_keyword, is_not_current_user
from ..models import Project

# User - Homepage
@user_app.route('', methods=['GET'])
def main():
	"""
	View homepage of user system at ``/user``.
	
	"""
	return render_template('user/index.html')

# User - View profile
@user_app.route('/<some_name>', methods=['GET','POST'])
@login_required 
def profile(some_name):
	"""
	View profile of an account within user system at ``/user/<some_name>``.
	
	Args:
		some_name (str): name of the user
	
	Returns:
		Project site if account is validated.

	Note:
		Show table of all user projects.
	
	Error:
		Error message emerges if there is no logged in user.
		
	"""
	# only between users in User-System, no access to an account 
	# (not currently signed in account) without providing password
	if is_not_current_user(user=current_user, current_name=some_name):
		flash(f'Your username is "{current_user.username}", you have no access to another account without password.', 'login')
		logout_user()
		return redirect(url_for('user.login', form=LoginForm()))

	# print all projects' information of current user within his profile
	projects = { i+1:{ 'p_name':project.p_name, 'name':project.name, 
						'description': project.description[:21]+"...", 'n_anno': project.anno_number, 
						'best': project.best_def, 'worst': project.worst_def }
						for i, project in enumerate(current_user.projects) } \
				if current_user.projects else None
	other_keys = ['n_anno', 'best', 'worst', 'description']

	# define style for the titles in table of projects
	title_styles = { '': '10', 'Project':'80', 'Number of annotators':'15', 
					"Definition of 'best'":'30', "Definition of 'worst'":'30', "Description":'100' }
	if projects:
		projects = projects.items()
	return render_template('user/profile.html', name=some_name, projects=projects, 
									styles=title_styles.items(), keys=other_keys)


# User - View project
@user_app.route('/<some_name>/<p_name>', methods=['GET','POST'])
@login_required 
def project(some_name, p_name):
	"""
	View user project at ``/user/<some_name>/<p_name>``.
	
	Args:
		some_name (str): user name.
		p_name (str): project name.
	
	Returns:
		project information.

	Error:
		Error message emerges if there is no logged in user.

	"""
	# only between users in User-System, no access to an account 
	# (not currently signed in account) without providing password
	if is_not_current_user(user=current_user, current_name=some_name):
		flash(f'Your username is "{current_user.username}", you have no access to another account without password.', 'login')
		logout_user()
		return redirect(url_for('user.login', form=LoginForm()))

	current_project = Project.query.filter_by(p_name=p_name, user=current_user).first()

	# get project informations
	project_name = current_project.name
	description = current_project.description
	n_anno = current_project.anno_number
	n_items = current_project.n_items
	mturk = current_project.mturk

	# define information of annotators
	n_anno_join = n_anno_left = 0
	batch_infos = []

	# infos from MTurk as the number of annotators are now referred to 
	# the number of annotations for each HIT (batch)
	if mturk:
		for i, batch in enumerate(current_project.batches):
			check_tuple = batch.tuples[0]

			# get n_anno_join, check the number of annotators who submit this batch
			n_anno_join = len(check_tuple.datas)

			# get n_anno_left
			# how many annotators this batch still needs
			n_anno_left = n_anno - n_anno_join

			batch_infos.append((i+1, n_anno_join, n_anno_left))

	# normal infos as the number of annotators stay the same
	else:
		# get n_anno_join, check the number of annotators who submit any batch of this project
		# it does not count if they log in and only save their annotations
		for annotator in current_project.annotators:
			if annotator.batches:
				n_anno_join += 1

		# get n_anno_left
		# how many annotators this project still needs
		n_anno_left = n_anno - n_anno_join

	return render_template('user/project.html', 
							name=some_name, project_name=project_name, p_name=p_name,
							n_anno=n_anno, n_items=n_items, description=description,
							n_anno_join=n_anno_join, n_anno_left=n_anno_left, 
							batch_infos=batch_infos, mturk=mturk,
							mturk_url=current_app.config['MTURK_SHOW_UP_URL'])
