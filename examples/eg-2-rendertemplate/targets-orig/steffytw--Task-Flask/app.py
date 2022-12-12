from flask import Flask,render_template,url_for,request,redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test.db'
db = SQLAlchemy(app)

class Todo(db.Model):
   id=db.Column(db.Integer,primary_key=True)
   context=db.Column(db.String(200),nullable=False)
   complete=db.Column(db.Integer,default=0)
   date_created=db.Column(db.DateTime,default=datetime.utcnow)
   def __repr__(self): 
      return '<Task %r>' % self.id

@app.route('/',methods=['POST','GET'])
def index():
   if request.method =='POST':
       task_content=request.form['content'] 
       new_task=Todo(context=task_content)
       try:
          db.session.add(new_task)
          db.session.commit()
          return redirect('/')
      
       except:
         return 'Issue in adding data'
   else:
      tasks=Todo.query.order_by(Todo.date_created).all()
      return render_template('index.html',tasks=tasks)

@app.route('/delete/<int:id>')
def delete(id):
   task_delete=Todo.query.get_or_404(id)
   try:
      db.session.delete(task_delete)
      db.session.commit()
      return redirect('/')
   except:
      return 'Problem in deleting that task'

@app.route('/update/<int:id>')
def update(id,methods=['POST','GET']):
   task= Todo.query.get_or_404(id)
   if request.method =='POST':
     pass
   else:
      tasks=Todo.query.order_by(Todo.date_created).all()
      return render_template('update.html',task=task)
   
if __name__ == "__main__":
   app.run(debug = True)