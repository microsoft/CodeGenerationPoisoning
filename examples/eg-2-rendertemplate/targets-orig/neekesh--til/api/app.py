from flask import Flask, render_template,url_for, request, redirect
from flask_sqlalchemy import  SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///til.db' #this is the route of the database
db = SQLAlchemy(app)#intializing database

class til(db.Model):
  id = db.Column(db.Integer, primary_key = True)
  date_created = db.Column(db.DateTime, default = datetime.utcnow)
  content = db.Column(db.String(2000), nullable= False)

  def __repr__(self):
    return '<TIl %r>' % self.id


@app.route('/', methods=['GET', 'POST'])
def submit():
  if request.method == 'POST':
    til_input = request.form['content']
    new_input = til(content=til_input)

    try:
      db.session.add(new_input)
      db.session.commit()
      return redirect('/veiw')
    except:
      return 'There was an issue in storing your data'
  else:

    return render_template('submit.html')

@app.route('/veiw')
def veiw():
  tild = til.query.order_by(til.date_created).all()

  return render_template('veiw.html', tild=tild)

if __name__ == '__main__':
  app.run( debug=True)