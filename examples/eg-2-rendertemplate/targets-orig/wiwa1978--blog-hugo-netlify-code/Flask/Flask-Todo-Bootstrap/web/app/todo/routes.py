from flask import request, render_template, redirect
from app.todo import todo
#from app.models import Task, db

from .. import db
from ..models import Task

@todo.route('/todos', methods=['POST', 'GET'])
def home():
   if request.method == "POST": 
       name = request.form['name']
       new_task = Task(name=name)
       db.session.add(new_task)
       db.session.commit()
       return redirect('/todos')
   else:
       tasks = Task.query.order_by(Task.created_at).all()  # add
   return render_template("todo/list.html", tasks=tasks)  # add

@todo.route('/todos/delete/<int:id>')
def delete(id):
   task = Task.query.get_or_404(id)

   try:
       db.session.delete(task)
       db.session.commit()
       return redirect('/todos')
   except Exception:
       return "There was a problem deleting data."


# update task
@todo.route('/todos/update/<int:id>', methods=['GET', 'POST'])
def update(id):
   task = Task.query.get_or_404(id)

   if request.method == 'POST':
       task.name = request.form['name']

       try:
           db.session.commit()
           return redirect('/todos')
       except:
           return "There was a problem updating data."

   else:
       title = "Update Task"
       return render_template('todo/update.html', title=title, task=task)
