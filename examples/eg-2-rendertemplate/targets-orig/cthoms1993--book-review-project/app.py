import os
from os import path
from flask import Flask, render_template, redirect, request, url_for, session, flash
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from flask_bcrypt import bcrypt

if path.exists("env.py"):
    import env

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get('SECRET_KEY')
app.config["MONGODB_NAME2"] = os.environ.get('MONGODB_NAME2')
app.config["MONGODB_NAME"] = os.environ.get('MONGODB_NAME')
app.config["MONGO_URI"] = os.environ.get('MONGO_URI')

mongo = PyMongo(app)
users = mongo.db.users
reviews = mongo.db.reviews


@app.route('/')
@app.route('/index')
def index():
    """landing page render"""
    return render_template('index.html')


@app.route('/login_page')
def login_page():
    """creates the ability to log in to your account if your username is recognised."""
    if 'username' in session:
        flash('welcome back!')
        return redirect(url_for('account'))

    return render_template('login.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User Login. If Username or password not found in MongoDB db 'users', flash message
        and redirect user to try again on Login page."""
    login_user = users.find_one({'name': request.form['username']})
    if login_user:
        if bcrypt.hashpw(request.form['pass'].encode('utf-8'),
                         login_user['password']) == login_user['password']:
            session['username'] = request.form['username']
        else:
            flash('incorrect username/and or password,please try again')
        return redirect(url_for('login_page'))
    return render_template('login.html')


@app.route('/register', methods=['POST', 'GET'])
def register():
    """User Registration. If Username is not taken and stored in MongoDB db
        'users'. Hashing passwords using Bcrypt.If username is already taken message flashed to user
        detailing same, if not on DB then account is created and redirected to your reviews page with flash message"""
    if request.method == 'POST':
        existing_user = users.find_one({'name': request.form['username']})
        if existing_user:
            flash('Username already taken, please try an alternative')
        else:
            hashpass = bcrypt.hashpw(request.form['pass'].encode('utf-8'), bcrypt.gensalt())
            users.insert({'name': request.form['username'], 'password': hashpass})
            session['username'] = request.form['username']
            flash('')
        return redirect(url_for('account'))

    return render_template('register.html')


@app.route('/logout')
def logout():
    """logs the user currently logged in out of the session."""
    session.clear()
    flash('you have logged out')
    return redirect(url_for('index'))


@app.route('/get_reviews')
def get_reviews():
    """displays all reviews in the reviews collection on the public review page"""
    return render_template("reviews.html", reviews=mongo.db.reviews.find())


@app.route('/add_review')
def add_review():
    """ adds a new review to the database"""

    return render_template("addreview.html")


@app.route('/update_review/<review_id>', methods=['POST'])
def update_review(review_id):
    """updates the review user has edited or changed"""
    reviews.update({'_id': ObjectId(review_id)},
                   {
                       'review_name': request.form.get('review_name'),
                       'book_name': request.form.get('book_name'),
                       'review_description': request.form.get('review_description'),
                       'rating': request.form.get('rating'),
                       'username': request.form.get('username'),
                       'author': request.form.get('author'),
                       'date': request.form.get('date'),
                       'book_cover': request.form.get('book_cover')
                   })
    flash('Reviews edited successfully')
    return redirect(url_for('account'))


@app.route('/insert_review', methods=['POST'])
def insert_review():
    reviews.insert_one(request.form.to_dict())
    flash('')
    return redirect(url_for('get_reviews'))


@app.route('/edit_review/<review_id>')
def edit_review(review_id):
    """edits the chosen review"""
    the_review = reviews.find_one({"_id": ObjectId(review_id)})
    return render_template('editreview.html', review=the_review)


@app.route('/delete_review/<review_id>')
def delete_review(review_id):
    """removes review from the database"""
    mongo.db.reviews.remove({'_id': ObjectId(review_id)})
    flash('review has been deleted')
    return redirect(url_for('account'))


@app.route('/account')
def account():
    """directs the user to there "my reviews"" page"""
    return render_template("account.html", reviews=mongo.db.reviews.find({'username': session.get('username')}))


@app.route('/contact')
def contact():
    """still in development"""
    return render_template('contact.html')


if __name__ == '__main__':
    app.run(host=os.environ.get('IP'),
            port=int(os.environ.get('PORT')),
            debug=True)
