from app import app, db

from flask_login import login_required, current_user
from flask import render_template, flash, redirect, url_for, session, logging, request
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import logging



# Home page
@app.route('/')
def index():	
	return render_template('home.html')




# Load todos from database
def getTodos():
	todos = Todos.query.filter_by(member_username=current_user.username).all()

	for todo in todos:
		if todo.completed:
			todo.completed = 'Done'
		else:
			todo.completed = 'Pending'
		todo.create_date = str(todo.create_date)
		todo.create_date = todo.create_date[0:10] 

	todos.sort(key=lambda x: x.completed, reverse=True)

	return todos



# pomodoro-tracker page
@app.route('/pomodoro', methods=["GET", "POST"])
@login_required
def pomodoro():
	session['registrationRedirect'] = False
	if request.method == 'POST':
		inputTimerTarget = request.form['pomodoroInterval']
		inputBreakTarget = request.form['breakInterval']

		# convert times to minutes:
		timerTarget = inputTimerTarget[3:]
		breakTarget = inputBreakTarget[3:]

		# save timer intervals for logged in user
		newTimerDetails = TimerDetails(member_username=current_user.username, pomodoro_interval=timerTarget, 
									   break_interval=breakTarget)
		db.session.add(newTimerDetails)
		db.session.commit()

		todos=getTodos()
		return render_template('pomodoro.html', todos=todos, timerTarget=timerTarget, breakTarget=breakTarget, 
												inputTimerTarget=inputTimerTarget, 
												inputBreakTarget=inputBreakTarget)
	else:
		timerDetails = TimerDetails.query.filter_by(member_username=current_user.username).first()
		todos=getTodos()
		if(timerDetails):
			inputTimerTarget = ('00:' + str(timerDetails.pomodoro_interval))
			inputBreakTarget = ('00:' + str(timerDetails.break_interval))
			return render_template('pomodoro.html', todos=todos, timerTarget=timerDetails.pomodoro_interval, 
													breakTarget=timerDetails.break_interval,
													inputTimerTarget=inputTimerTarget,
													inputBreakTarget=inputBreakTarget)
		else:
			timerTarget = '25'
			breakTarget = '5'
			return render_template('pomodoro.html', todos=todos, timerTarget=timerTarget, breakTarget=breakTarget, 
													inputTimerTarget=timerTarget, inputBreakTarget=breakTarget)


# todos manager
@app.route('/todos', methods=["GET", "POST"])
@login_required
def todos():
	todos = getTodos()	
	return render_template('todos.html',todos=todos)


# add new todos
@app.route('/add_todo', methods=["GET", "POST"])
@login_required
def add_todo():
	if request.method == 'POST':
		category = request.form['category']
		description = request.form['description']

		if category and (len(str(description).strip()) != 0):
			newTodo = Todos(member_username=current_user.username, category=category, 
							description=description, completed=False)
			db.session.add(newTodo)
			db.session.commit()
			todos = getTodos()
			return redirect(url_for('todos', todos=todos))
		else:
			flash('Please enter complete details', 'danger')
			return render_template('add_todo.html')
	else: 
		return render_template('add_todo.html')


# edit todos
@app.route('/edit_todo/<string:id>', methods=["GET", "POST"])
@login_required
def edit_todo(id):
	editTodo = Todos.query.filter_by(id=id).first()
	if request.method == 'POST':
		editTodo.category = request.form['category']
		editTodo.description = request.form['description']
		if request.form['status'] == 'Done':
			editTodo.completed = True
		else:
			editTodo.completed = False
		db.session.commit()

		todos = getTodos()
		return redirect(url_for('todos',todos=todos))
	else:
		if editTodo and editTodo.member_username == current_user.username:
			return render_template('edit_todo.html',editTodo=editTodo)

# delete todos
@app.route('/delete_todo/<string:id>', methods=["POST"])
@login_required
def delete_todo(id):
	delTodo = Todos.query.filter_by(id=id).first()
	db.session.delete(delTodo)
	db.session.commit()
	todos = getTodos()
	return redirect(url_for('todos', todos=todos))


# feedback page
@app.route('/feedback', methods=["GET", "POST"])
def feedback():	
	if request.method == 'POST':
		member_username = "guest"
		feedback = request.form['feedback']
		if session['logged_in']:
			member_username = current_user.username

		newFeedback = Feedbacks(member_username=member_username, feedback=feedback)
		db.session.add(newFeedback)
		db.session.commit()

		flash('Submission successful! Thank you for your feedback.', 'success')
		return render_template('feedback.html')
	else: 		
		return render_template('feedback.html')