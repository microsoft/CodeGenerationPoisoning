from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from data import Blogs

from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap
# from flask_wtf import FlaskForm
# from wtform import StringField, PasswordField, BooleanField	
# from wtform.validators import InputRequired, Length
#import flask_whooshalchemy
 
app = Flask(__name__)
app.secret_key = "yuisdu23423423jkjhhgj32gjh32g_EJGSAJFJHAGF"

Bootstrap(app)



Blogs = Blogs()

@app.route('/')
def index():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/profile')
def profile():
    return render_template('profile.html')    

@app.route('/loginprocess', methods=['GET', 'POST'])
def loginprocess():
    response = request.form
    session['username'] = response['username']
    return redirect('/')

@app.route('/registerprocess', methods=['GET', 'POST'])
def registerprocess():
    response = request.form
    if 'usertype' in response:
        session['usertype'] = response['usertype']
    session['username'] = response['username']
    session['email'] = response['email']
    session['mobile'] = response['mobile']
    session['address'] = response['address']
    session['fax'] = response['fax']
    session['company'] = response['company']
    return redirect('/')

@app.route('/logout')
def logout():
	session.clear()
	return redirect('/')

@app.route('/products')
def products():
    return render_template('products.html')
    

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/register')
def register():
    return render_template('register.html')


@app.route('/blogs')
def blogs():
    return render_template('blogs.html', blogs = Blogs)

@app.route('/blogs/<string:id>/')
def blog(id):
    return render_template('blog.html', id = id)

if __name__ == '__main__':
    app.run(debug=True)