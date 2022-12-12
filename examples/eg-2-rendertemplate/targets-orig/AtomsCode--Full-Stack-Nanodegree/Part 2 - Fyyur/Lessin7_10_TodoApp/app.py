from flask import Flask, render_template, request, redirect, url_for, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import sys

app = Flask(__name__)

# Database Configuaration
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:1234@127.0.0.1:5432/test'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Adding Migrate library
migrate = Migrate(app, db)

# Create Table todos in the Database with two column id , description


class Todo(db.Model):
    __tablename__ = 'todos'
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(), nullable=False)
    completed = db.Column(db.Boolean(), nullable=False, default=False)
    todolist_id = db.Column(db.Integer, db.ForeignKey(
        'todolists.id'), nullable=False)


class TodoLists(db.Model):
    __tablename__ = 'todolists'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(), nullable=False)
    todos = db.relationship('Todo', backref='list', lazy=True)

# Used for debug Mode


def __repr__(self):
    return f'<Todo id:{self.id} , descripiton:{self.description}>'


# all routes will be here
@app.route('/todos/create', methods=['POST'])
def create_todo():
    error = False
    body = {}
    try:
        # This have been change from - description = request.form.get_json()['description']
        description = request.get_json()['description']

        todo = Todo(description=description)
        db.session.add(todo)
        db.session.commit()
        body['description'] = todo.description
    except:
        error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()
    if error:
        abort(400)
    else:
        return jsonify(body)


@app.route('/todos/<todo_id>/set-completed', methods=['POST'])
def set_completed_todo(todo_id):
    error = False
    body = {}
    try:
        completed = request.get_json()['comleted']
        todo = Todo.query.get(todo_id)
        todo.completed = completed
        db.session.commit()
    except:
        error = True
        db.session.rollback()
        print(sys.exc_info())
    finally:
        db.session.close()
        return redirect(url_for('index'))


@app.route('/todos/<todo_id>/Delete-Todo', methods=['DELETE'])
def delete_todo(todo_id):
    error = False
    body = {}
    try:
        Todo.query.filter_by(id=todo_id).delete()
        db.session.commit()
    except:
        db.session.rollback()
    finally:
        db.session.close()
    return jsonify({'success': True})


@app.route('/list/<list_id>')
def get_list_todos(list_id):
    return render_template('index.html',
                           lists=TodoLists.query.all(),
                           active_list=TodoLists.query.get(list_id),
                           todos=Todo.query.filter_by(todolist_id=list_id).order_by('id').all())


@app.route('/')
def index():
    return redirect(url_for('get_list_todos', list_id=1))
