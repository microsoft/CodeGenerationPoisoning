# -*- coding: utf-8 -*-
"""
Views
#################

*Module* ``project.annotator.views``

This module defines routes to manage views for annotators.

"""

from flask_login import login_required, current_user
from flask import render_template
from . import annotator_app
from .helpers import batches_list

# Annotator - Project page with all batches
@annotator_app.route('/<p_name>', methods=['GET'])
@login_required
def project(p_name):
	"""
	View project with all batches corresponding to given keyword at ``/annotator/<p_name>``.
	
	Args:
		p_name (str): project name
		
	Returns:
		Status of each batch in project if they are submitted by this annotator or not.
	
	"""

	# current_user in flask_login is now the current logged in annotator
	current_project = current_user.project

	# check whether this annotator has submitted this batch, if yes, this batch is no longer active.
	check_batches = []
	for batch in current_project.batches:
		if batch in current_user.batches:
			check_batches.append(True)
		else:
			check_batches.append(False)

	return render_template('annotator/project.html', 
							batches_links=batches_list(p_name, n_batches=len(current_project.batches)),
							zip=zip, check=check_batches, project=current_project)
