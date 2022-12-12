from flask import render_template
from flask import request, redirect, url_for

from flask_security import login_required
from flask_login import logout_user

from app import app, db
from admin import University, Faculty


@app.route("/logout")
def logout():
    logout_user()
    return redirect('login')

@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    obj = db.session.query(University).paginate(page=page, per_page=5)
    return render_template('index.html', n=obj)
    


@app.route('/detail/<int:pk>/')
def detail(pk):
    univer = db.session.query(University).filter(University.id==pk).first()
    faculty = db.session.query(Faculty).filter(Faculty.univer_id==pk)
    return render_template('detail.html', univer=univer, fac=faculty)