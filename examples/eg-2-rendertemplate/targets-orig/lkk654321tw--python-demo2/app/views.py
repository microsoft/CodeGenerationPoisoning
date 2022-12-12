from flask import render_template
from flask import flash
from flask import redirect
from app import app
from .forms import LoginForm

#@app.route('/')
@app.route('/login',methods = ['GET','POST'])
def login():
  form=LoginForm()
  if form.validate_on_submit():
    flash('Login required for OpenID="'+ form.openid.data +'", remmber_me=' + str(form.remember_me.data))
    return redirect('/index')
  return render_template("login.html",
    title = 'Login',
    form =form,
    providers = app.config['OPENID_PROVIDERS'])

#@app.route('/index')
def index():
#  return "hello simon"
  user={'nickname':'Lkk'} # fake user
  return render_template("index.html",
     title='Hpme',
     user= user)
   
  
