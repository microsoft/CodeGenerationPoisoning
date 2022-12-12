# -*- coding: utf-8 -*-
"""
Accounts
##########

*Module* ``project.annotator.account``

This module defines routes to manage accounts of annotators.

"""

from flask_login import login_user
from flask import render_template, redirect, url_for
from . import annotator_app
from .forms import AnnoCheckinForm
from .. import db
from ..models import Annotator


# Annotator - main page
@annotator_app.route('', methods=['GET', 'POST'])
def login():
	"""
	Manage account login with keyword and (pseudo)name inside annotator system at ``/annotator``.
	
	Returns:
		project site ``/annotator/<p_name>`` if account is valid.
	
	Error:
		Error message emerges if keyword or name is invalid.
	
	"""
	form = AnnoCheckinForm()
	if form.validate_on_submit():
		annotator = Annotator.query.filter_by(keyword=form.keyword.data).first()
		
		# a new annotator uses this keyword, saves his name in the database 
		# and this keyword is no longer available for anyone else
		if not annotator.name:
			annotator.name = form.name.data
			db.session.commit()

		login_user(annotator)
		current_project = annotator.project
		p_name = current_project.p_name

		return redirect(url_for('annotator.project', p_name=p_name))
	return render_template('annotator/index.html', form=form)
