from flask import Flask, render_template, url_for, request, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.utils import secure_filename
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from flask import Blueprint, request, render_template, \
                  jsonify, g, session, redirect, make_response

import os


PATH = os.getcwd()
UPLOAD_FOLDER = "/static/uploads"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///receiptBase.db'

db = SQLAlchemy(app)



def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class Receipt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    content = db.Column(db.String(200), default="Details..")
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    tag = db.Column(db.String(30), nullable=False, default="Common Expenses")
    belonging_user_id = db.Column(db.Integer, primary_key=False)
    total_cost = db.Column(db.Float, nullable=False, default=25)
    location = db.Column(db.String(100), nullable=False, default="Ankara")
    photo_path = db.Column(db.String(100), nullable=False, default="")
    

class Users(db.Model):                  #users icin ikinci database class'i. bind key kullanarak database'e erisecek
    
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(50), default="test User", nullable=False)
    password = db.Column(db.String(50), nullable=False)
    address = db.Column(db.String(50), default="Sogutozu St. TOBB ETU, Ankara Turkey",nullable=False)
    phone = db.Column(db.String(50), default="+905067350522",nullable=False)
    email = db.Column(db.String(50), default="testuser@testaccount.com", nullable=False)

    def __repr__(self):
        return '<Receipt %r>' % self.id


@app.route('/<int:user_id>/', methods=['GET'])
def index_user(user_id):

    
    receipts = Receipt.query.filter_by(belonging_user_id = user_id).all()
    user = Users.query.get_or_404(user_id)

    return render_template('index.html', receipts=receipts, user=user)
@app.route('/<int:user_id>/', methods=['POST'])
def index_user1(user_id):

	print("DONE")
	user = Users.query.get_or_404(user_id)

	receipt_name = request.form['name']
	receipt_location = request.form['location']
	receipt_tag = request.form['tag'] 
	receipt_total_cost = request.form['total_cost']


	file = request.files['file']

	if file and allowed_file(file.filename):
		filename = secure_filename(file.filename)
		file.save(os.path.join(PATH + UPLOAD_FOLDER, filename))
		receipt_photo_path = os.path.join(UPLOAD_FOLDER, filename)
	else:
		receipt_photo_path = ""


	new_receipt = Receipt(name=receipt_name,total_cost=receipt_total_cost, location=receipt_location, tag=receipt_tag, photo_path=receipt_photo_path, belonging_user_id=user.user_id)


	try:

		print("DONE2")
		db.session.add(new_receipt)
		db.session.commit()
		receipts = Receipt.query.filter_by(belonging_user_id = user_id).all()
		return render_template('index.html', receipts=receipts, user=user)
	except:
		return 'There was an issue adding your receipt'

@app.route('/login', methods=['GET', 'POST'])
def login():
        
        if request.method == 'POST':
            strname = request.form['username']
            strpassword=request.form['password']

            user = Users.query.filter_by(username = strname).first()

            if user and user.password == strpassword:
                return index_user(user.user_id)
            else:
            	return make_response('Username or password is incorrect!', 401)
        

        return render_template('Login.html')

@app.route('/signupform', methods=['GET', 'POST'])
def signup():

	if request.method == 'POST':
	
		data = request.form
		username = data['username']
		email = data['email']
		password = data['password']
		name = data['name']
		

		new_user = Users(username = username, email = email , password=password, name=name)
			
		db.session.add(new_user)
		db.session.commit()

		return redirect('/login')
	else:
		return render_template('Register.html')

        

@app.route('/<int:user_id>/delete/<int:id>')
def delete(user_id, id):
    receipt_to_delete = Receipt.query.get_or_404(id)

    try:
        db.session.delete(receipt_to_delete)
        db.session.commit()
        return index_user(user_id)
    except:
        return 'There was a problem deleting that receipt'

@app.route('/<int:user_id>/details/<int:id>', methods=['GET', 'POST'])
def details(user_id, id):
    receipt = Receipt.query.get_or_404(id)
    user = Users.query.get_or_404(user_id)

    if request.method == 'POST':
        try:
            return details(user_id, id)
        except:
            return 'There was an issue detailing your receipt'
    else:
        return render_template('details.html', receipt=receipt, user=user)


@app.route('/<int:user_id>/share/<int:id>', methods=['GET', 'POST'])
def share(user_id, id):

    receipt = Receipt.query.get_or_404(id)
    user = Users.query.get_or_404(user_id)

    if request.method == 'POST':
        try:
            return index_user(user_id)
        except:
            return 'There was an issue'
    else:
        return render_template('Share.html', receipt=receipt, user=user)

@app.route('/<int:user_id>/share/<int:id>/', methods=['GET'])
def share_view(user_id, id):

    receipt = Receipt.query.get_or_404(id)
    user = Users.query.get_or_404(user_id)

    return render_template('ShareView.html', receipt=receipt, user=user)


@app.route('/<int:user_id>/update/<int:id>', methods=['GET', 'POST'])
def update(user_id, id):
    user = Users.query.get_or_404(user_id)
    receipt = Receipt.query.get_or_404(id)


    if request.method == 'POST':
        receipt.name = request.form['name']
        receipt.total_cost = request.form['total_cost']
        receipt.tag = request.form['category']
        receipt.location = request.form['location']
        date_created = request.form['date_created']

        file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(PATH + UPLOAD_FOLDER, filename))
            receipt.photo_path = os.path.join(UPLOAD_FOLDER, filename)
        else:
            receipt_photo_path = ""

        #Convert browser date format to sqlite date format 
        Ddate_created = datetime.strptime(date_created, '%Y-%m-%d')
        
        receipt.date_created = Ddate_created.date()

        try:
            db.session.commit()
            return index_user(user.user_id)
        except:
            return 'There was an issue updating your receipt'

    else:
        return render_template('update.html', receipt=receipt, user=user)

@app.route('/updateUser/<int:user_id>', methods=['GET', 'POST'])
def update_user(user_id):

    user = Users.query.get_or_404(user_id)

    if request.method == 'POST':
        user_username = request.form['name']
        user_address = request.form['address']
        user_email = request.form['email']
        user_phone = request.form['phone']

        change = 0

        if user_username != "":
            user.name = user_username
            change = 1
        if user_email != "":
            user.email = user_email
            change = 1
        if user_phone != "":
            user.phone = user_phone
            change = 1
        if user_address != "":
            user.address = user_address
            change = 1

        try:

            if change == 1:
                db.session.add(user)
                db.session.commit()

            return index_user(user.user_id)
        except:
            return 'There was an issue updating your details'
    else:
        return render_template('userSettings.html', user=user)



@app.route('/<int:user_id>/enter_details/<int:id>', methods=['GET', 'POST'])
def enter_details(user_id, id):
    receipt = Receipt.query.get_or_404(id)
    user = Users.query.get_or_404(user_id)    

    if request.method == 'POST':
        receipt.content = request.form['content']

        try:
            db.session.commit()
            return render_template('details.html', receipt=receipt, user=user)
        except:
            return 'There was an issue updating your receipt details'

    else:
        return render_template('update_2.html', receipt=receipt, user=user)

@app.route('/search/<int:user_id>',  methods=['GET', 'POST'])
def search_results(user_id):
    if request.method == 'POST':
    	receipts = Receipt.query.filter_by(belonging_user_id = user_id)
    	search_string = request.form['search']
    	searchBox = request.form.getlist('searchBox')

    	if(search_string==""):
	       	return render_template('index.html', receipts = receipts.all(), user=Users.query.get_or_404(user_id))
    	if(len(searchBox)==0):
	        	
        	receipts1 = Receipt.query.filter(Receipt.name.like(search_string + "%")) 
	        receipts2 = Receipt.query.filter(Receipt.location.like(search_string + "%"))
	        receipts3 = Receipt.query.filter(Receipt.tag.like(search_string + "%"))   
	        receiptsFinal = receipts1.union(receipts2).union(receipts3)
	        receiptsFinal = receiptsFinal.intersect(receipts).all()
    	elif(len(searchBox)==1):
    		if(searchBox[0]=="1"):
		        receipts1 = Receipt.query.filter(Receipt.name.like(search_string + "%"))
		        receiptsFinal = receipts1.intersect(receipts).all()
    		elif(searchBox[0]=="2"):
		        receipts2 = Receipt.query.filter(Receipt.location.like(search_string + "%"))
		        receiptsFinal = receipts2.intersect(receipts).all()
    		elif(searchBox[0]=="3"):
		        receipts3 = Receipt.query.filter(Receipt.tag.like(search_string + "%"))
		        receiptsFinal = receipts3.intersect(receipts).all() 
    	elif(len(searchBox)==2):
	        if(searchBox[0]=="1" and searchBox[1]=="2"):
	            receipts1 = Receipt.query.filter(Receipt.name.like(search_string + "%"))
	            receipts2 = Receipt.query.filter(Receipt.location.like(search_string + "%"))
	            receiptsFinal = (receipts1.union(receipts2)).intersect(receipts).all()
	        if(searchBox[0]=="1" and searchBox[1]=="3"):
	            receipts1 = Receipt.query.filter(Receipt.name.like(search_string + "%"))
	            receipts3 = Receipt.query.filter(Receipt.tag.like(search_string + "%"))
	            receiptsFinal = (receipts1.union(receipts3)).intersect(receipts).all()
	        if(searchBox[0]=="2" and searchBox[1]=="3"):
	            receipts3 = Receipt.query.filter(Receipt.tag.like(search_string + "%"))
	            receipts2 = Receipt.query.filter(Receipt.location.like(search_string + "%"))
	            receiptsFinal = (receipts2.union(receipts3)).intersect(receipts).all()
    	elif(len(searchBox)==3):
	        receipts1 = Receipt.query.filter(Receipt.name.like(search_string + "%")) 
	        receipts2 = Receipt.query.filter(Receipt.location.like(search_string + "%"))
	        receipts3 = Receipt.query.filter(Receipt.tag.like(search_string + "%"))   
	        receiptsFinal = (((receipts1.union(receipts2)).union(receipts3)).intersect(receipts)).all()

	               
    	return render_template('index.html', receipts=receiptsFinal, user=Users.query.get_or_404(user_id))


if __name__ == "__main__":
    app.run(debug=True)
