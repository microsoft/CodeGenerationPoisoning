from flask import Flask , render_template, request , redirect, jsonify
from flask_sqlalchemy import SQLAlchemy, Model
from sqlalchemy import Column , ForeignKey, Integer, String
import sys
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:1@localhost:5432/todo'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
class List(db.Model):
    __tablename__ = 'lists'
    id = Column(Integer,primary_key = True)
    name = Column(String(),nullable = False)
    def __repr__ (self):
        return 'List ' + str(self.id) + ': ' + self.name
class Item(db.Model):
    __tablename__ = 'items'
    id = Column(Integer,primary_key = True)
    content = Column(String(),nullable = False)
    lid = Column(Integer,ForeignKey('lists.id'))

    def __repr__ (self):
        return  self.content

@app.route('/')
def index():    
    return render_template('index.html',data=Item.query.all())

# ****************** FORM get data via request.form **************************
@app.route('/register',methods=["POST"])
def register():
    print("*******************")
    print(request.form.get('name') )
    print(request.form.get('r') )
    # redirect emits the /registrans route to be listened in the registerans function
    return redirect('/registerans')

@app.route('/registerans')
def registerans():
    return render_template('index.html',data=List.query.all())
# ***************************************************

# recevie msgs from view via the url    /ray2?ray2=54
# method is by default is GET
@app.route('/ray2')
def getUserURLInput():
    print(request.args.get('ray2'))
    return render_template('index.html')

@app.route('/create_new_todo',methods=["POST"])
def create_new_todo():
    json_data = request.get_json()
    Content = json_data['content']
    # it returns the request again as a response
    print(jsonify({"content":Content}))
    return jsonify(     {"content":Content}    )

if __name__ == '__main__':
    app.run()
