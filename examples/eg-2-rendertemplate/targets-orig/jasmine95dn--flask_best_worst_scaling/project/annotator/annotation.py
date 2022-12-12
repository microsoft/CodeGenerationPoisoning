# -*- coding: utf-8 -*-
"""
Annotations
######################

*Module* ``project.annotator.annotation``

This module defines routes to manage the annotations.

"""

from flask_login import login_required, current_user
from flask import render_template, redirect, url_for, flash, request
from . import annotator_app, hit_app
from .forms import TupleForm
from .. import db
from ..models import Project, Data, Batch


# Annotator - A batch of the project
@annotator_app.route('/<p_name>/batch-<int:batch_id>', methods=['GET', 'POST'])
@login_required
def batch(p_name, batch_id):
	"""
	Represent a batch within the project in the local system for an annotator 
	to annotate at ``/annotator/<p_name>/batch-<int:batch_id>``.

	Args:
		p_name (str): name of the project 
		batch_id (int): id of the batch

	Returns: 
		project site with all batches at ``/annotator/<p_name>``, 
		if the annotation is saved or the valid annotation is submitted.

	Error:
		Error message emerges if invalid annotation is submitted.
	"""

	# information of this project
	# current_user in flask_login is now the current logged in annotator
	current_annotator = current_user
	current_project = current_annotator.project
	best = current_project.best_def
	worst = current_project.worst_def
	description = current_project.description

	current_batch = current_project.batches[batch_id-1]
	question_number = range(1, current_batch.size+1)

	# in case some people still want to change their submitted results by typing route 
	# instead of clicking on button though this button is already deactivated
	if current_batch in current_annotator.batches: 
		flash(f'Batch {batch_id} already submitted!', 'action')
		return redirect(url_for('annotator.project', p_name=p_name))

	# initialization of all forms
	forms = [TupleForm(prefix='question-'+str(i)) for i in question_number]
	tuples = []
	
	# dynamic choices and dynamic default value (if exists) for each RadioField attribute
	for form, tuple_ in zip(forms, current_batch.tuples):
	
		form.best_item.choices = [(item.id, item.item) for item in tuple_.items]
		form.worst_item.choices = [(item.id, item.item) for item in tuple_.items]

		# check if this annotator has saved their data before
		if Data.query.filter_by(annotator=current_annotator, tuple_=tuple_).first():
			data = Data.query.filter_by(annotator=current_annotator, tuple_=tuple_).first()

			form.best_item.default = data.best_id
			form.worst_item.default = data.worst_id

		# this is literally defined for Items that have String-Format!, must change for others
		tuples.append(', '.join([item.item for item in tuple_.items]))

	if request.method == 'POST':

		# Submit Button
		if request.form['action'] == 'submit':

			# in case this person has opened this batch more than once and already submitted 
			# but still wants to submit this batch again
			if current_batch in current_annotator.batches:
				flash(f'Batch {batch_id} already submitted!', 'action')
				return redirect(url_for("annotator.project", p_name=p_name))

			if all([form.validate_on_submit() for form in forms]):

				for form, tuple_ in zip(forms, current_batch.tuples):
					if Data.query.filter_by(annotator=current_annotator, tuple_=tuple_).first():
						data = Data.query.filter_by(annotator=current_annotator, tuple_=tuple_).first()
						data.best_id = form.best_item.data
						data.worst_id = form.worst_item.data

					else:
						Data(best_id=form.best_item.data, worst_id=form.worst_item.data, 
								tuple_=tuple_, annotator=current_annotator)
				current_annotator.batches.append(current_batch)
				db.session.commit()
				flash(f'Batch {batch_id} successfully submitted!', 'action')
				
				return redirect(url_for("annotator.project", p_name=p_name))
					
		# Save Button
		elif request.form['action'] == 'save':
			for form, tuple_ in zip(forms, current_batch.tuples):
				if Data.query.filter_by(annotator=current_annotator, tuple_=tuple_).first():
					data = Data.query.filter_by(annotator=current_annotator, tuple_=tuple_).first()
					data.best_id = form.best_item.data
					data.worst_id = form.worst_item.data

				else:
					Data(best_id=form.best_item.data, worst_id=form.worst_item.data, 
							tuple_=tuple_, annotator=current_annotator)
			
			db.session.commit()
			flash(f'Batch {batch_id} saved!', 'action')
			return redirect(url_for("annotator.project", p_name=p_name))  
	
	return render_template('annotator/batch.html', best=best, worst=worst, description=description, 
							 zip=zip, batch_form=forms,  question_number=question_number, 
							tuples=tuples, p_name=p_name, batch_id=batch_id, int=int, 
							tuple_size=len(tuple_.items))

# MTurk - A batch of a project

@hit_app.route('/<p_name>/<hit_id>', methods=['POST', 'GET'])
def hit(p_name, hit_id):
	"""
	Represent a HIT within the project directed from MTurk for an annotator (turker) 
	to annotate at ``/mturk/<p_name>/<hit_id>``.

	Args:
		p_name (str): name of the project 
		hit_id (str): id of the HIT

	Returns: 
		keyword of the HIT, if valid annotation is submitted.

	Error:
		Error message emerges if invalid annotation is submitted.
	"""
	# information of this project
	current_project = Project.query.filter_by(p_name=p_name).first()
	best = current_project.best_def
	worst = current_project.worst_def
	description = current_project.description

	current_batch = Batch.query.filter_by(project=current_project, hit_id=hit_id).first()

	# if the number of time this batch is submitted already meets the number of required annotations,
	# anyone tries to access this batch by typing route will not see the batch anymore
	first_tuple = current_batch.tuples[0]
	if len(first_tuple.datas) >= current_project.anno_number:
		return '<h2> This HIT is no longer available! </h2>'

	question_number = range(1, current_batch.size+1)

	# initialization of all forms
	forms = [TupleForm(prefix=str(i)) for i in question_number]
	tuples = []
	
	# dynamic choices for each RadioField attribute
	for form, tuple_ in zip(forms, current_batch.tuples):
		form.best_item.choices = [(item.id, item.item) for item in tuple_.items]
		form.worst_item.choices = [(item.id, item.item) for item in tuple_.items]

		tuples.append(', '.join([item.item for item in tuple_.items]))

	# Submit
	if all([form.validate_on_submit() for form in forms]):
		for form, tuple_ in zip(forms, current_batch.tuples):
			new_data = Data(best_id=form.best_item.data, worst_id=form.worst_item.data, tuple_=tuple_)
			db.session.add(new_data)
		db.session.commit()

		return f'''<h2> Your batch is submitted succesfully. Here is your keyword: 
				<strong> {current_batch.keyword} </strong> </h2> '''

	return render_template('annotator/batch.html', best=best, worst=worst, description=description, 
							 zip=zip, batch_form=forms,  question_number=question_number, 
							  tuples=tuples, hit_id=hit_id, int=int, mturk=current_project.mturk)
