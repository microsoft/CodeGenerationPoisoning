from flask import Flask , render_template, request , redirect, jsonify  , flash
from flask_sqlalchemy import SQLAlchemy, Model 
from sqlalchemy import Column , ForeignKey, Integer, String, Boolean , orm 
import sys
app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:1@localhost:5432/todo'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class List(db.Model):
    __tablename__ = 'lists'
    id = Column(Integer,primary_key = True)
    name = Column(String(),nullable = False)
    items = db.relationship('Item',backref='list',lazy = True,  cascade='all,delete')
    def __repr__ (self):
        return 'List ' + str(self.id) + ': ' + self.name

class Item(db.Model):
    __tablename__ = 'items'
    id = Column(Integer,primary_key = True)
    content = Column(String(),nullable = False)
    completed = Column(Boolean ,default= False)
    lid = Column(Integer,ForeignKey('lists.id'))

    def __repr__ (self):
        return  self.content

@app.route('/')
def index():    
    randomList = List.query.first()
    if not randomList:
        return render_template("index.html")

    random_list_id = randomList.id
    return render_template('index.html',data=Item.query.filter(Item.lid == random_list_id).order_by('id').all(),lists = List.query.order_by('id').all() ,
    activeList = random_list_id )

@app.route('/list/<list_id>')
def index_with_list(list_id):
    print(list_id)
    return render_template('index.html',data=Item.query.filter(Item.lid == list_id).order_by('id').all(),lists = List.query.order_by('id').all() ,
     activeList = list_id )
     
@app.route('/list/delete/<list_id>')
def deleteList(list_id):
    try:
        List.query.filter(List.id==list_id).delete()
        db.session.commit()
        return redirect("/")
    except :
        print("cannot delete list id: ",list_id)
        # no content
        return ('',204)

@app.route("/list/add",methods=["POST"])
def addList():
    json = request.get_json()
    listName = json["name"]
    id = int(-1)
    try:
        list = List(name=listName)
        db.session.add(list)
        db.session.commit()
        id = list.id
        print('done',id,listName)
    except:
        db.session.rollback()
    finally:
        db.session.close()
    # if it is a vaild id
    if(id >= 0):    
        return jsonify ( {"id":id} )
    
@app.route('/todo/delete', methods=["POST"])
def deleteItem():
    try:
        json = request.get_json()
        deleted_id = json['id']
        Item.query.filter_by(id=deleted_id).delete()
        db.session.commit()

        print(id)
    except:
        db.session.rollback()
        print("failed to delete")
        return jsonify({'sucess': False})
    finally :
        db.session.close()

    return jsonify({'sucess': True})

@app.route('/todo/update/<item_id>/<item_checked>',methods=["GET"])
def updateItems(item_id,item_checked):
    try:
        id = item_id
        item = Item.query.get(id)
        # the url argument is just a string so we need to convert it to boolean
        print("cccc",item_checked)
        if item_checked == "false":
            item.completed = False
        elif item_checked == "true":
            item.completed = True
        db.session.commit()
        print(id,item.completed)
    except :
        db.session.rollback()
        print("error update checkbox server")
    finally :
        db.session.close()
    # return no content , don't change anyting
    return ('', 204)

@app.route('/todo/add',methods=["POST"])
def create_new_todo():
    body = ''
    id = 1
    error = False
    try:
        # get_json data
        json_data = request.get_json()
        Content = json_data['content']
        list  = json_data['activeList']
        item = Item(content=Content,lid= list)
        # we just do that because we can't used the item.content in the return value after we commit the database
        body = item.content
        db.session.add(item)
        # if any exception is throw before that line so it will not commit and will go to the except block to rollback
        db.session.commit()
        id = item.id
    except:
        # clear the pending transactions or pending SQL Instructions (uncommited transactions)
        db.session.rollback()
        print("Exception not Ray2 :",sys.exc_info())
        error=True
    finally:
        db.session.close()

    # check for exception not to return a rubbish json
    if not error:
        # returns json response not an html , this is an API
        return jsonify(     {"content":body,
                             "id" : id}    )


if __name__ == '__main__':
    app.run(host="localhost", port=8008)
