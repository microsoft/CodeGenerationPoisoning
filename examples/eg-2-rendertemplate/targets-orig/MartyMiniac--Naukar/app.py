from flask import *
from datetime import datetime
from requestDatabase import requestDatabase
import pytz

app = Flask(__name__)
db = requestDatabase()

@app.route('/', methods=['POST','GET'])
def index():
    if request.method=="POST":
        task_content = request.form['content']
        IST = pytz.timezone('Asia/Kolkata') 
        dt_string = datetime.now(IST).strftime("%d/%m/%Y %I:%M:%S %p")
        db.add(task_content, dt_string)
        return redirect('/')
    else:
        tasks = db.getAll()
        return render_template('index.html', tasks=tasks, length=db.len())


@app.route('/delete/<string:id>')
def delete(id):
    db.delete(id)
    return redirect('/')

@app.route('/update/<string:id>', methods=['GET','POST'])
def update(id):
    if request.method == 'POST':
        print(request)
        task_content = request.form['content']
        db.update(id, task_content)
        return redirect('/')
    else:
        tasks = db.get(id)
        return render_template('update.html', task=tasks)

if __name__ == "__main__":
    app.run(debug=True)