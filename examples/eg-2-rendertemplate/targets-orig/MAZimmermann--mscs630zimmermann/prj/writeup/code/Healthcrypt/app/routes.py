# IMPORT STATEMENTS ----- ----- ----- ----- -----

from flask         import render_template, flash, redirect, url_for, request, session

from flask_login   import login_user, logout_user, current_user, login_required

from werkzeug.urls import url_parse

from app           import app, db

from app.forms     import LoginForm, RegistrationForm, RecordForm

from app.models    import Physician, Record

from cryptography.fernet import Fernet

from datetime      import datetime

import hashlib as h





# ----- ----- ----- ----- ----- ----- ----- ----- ----- -----
# ROUTES

# ----- ----- ----- ----- ----- ----- ----- ----- ----- -----
# LOGIN
@app.route("/",      methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():

  if current_user.is_authenticated:
    
    physician = current_user
    
    next_page = request.args.get("next")

    if not next_page or url_parse(next_page).netloc != "":

      next_page = url_for("physician", username=physician.username)

    return redirect(next_page)

  form = LoginForm()

  if form.validate_on_submit():

    physician = Physician.query.filter_by(username=form.username.data).first()

    attemptedpwd = h.md5(form.password.data.encode())

    attemptedpwd = attemptedpwd.hexdigest()

    if physician is None:

      flash("Invalid Username or Password")

      return redirect(url_for("login"))

    elif attemptedpwd != physician.get_password():

      flash("Invalid Username or Password")

      return redirect(url_for("login"))

    login_user(physician)

    next_page = request.args.get("next")

    if not next_page or url_parse(next_page).netloc != "":

      next_page = url_for("physician", username=physician.username)

    return redirect(next_page)

  return render_template("login.html", form=form)





# ----- ----- ----- ----- ----- ----- ----- ----- ----- -----
# LOGOUT
@app.route("/logout")
def logout():

  logout_user()

  return redirect(url_for("login"))





# ----- ----- ----- ----- ----- ----- ----- ----- ----- -----
# PHYSICIAN
@app.route("/physician/<username>")
@login_required
def physician(username):
  
  physician = Physician.query.filter_by(username=username).first_or_404()

  key = physician.get_key()

  page = request.args.get("page", 1, type=int)

  records = physician.records.order_by(Record.date_created.desc()).paginate(
    page, 2, False)

  next_url = url_for("physician", username=physician.username, page=records.next_num)\
    if records.has_next else None

  prev_url = url_for("physician", username=physician.username, page=records.prev_num)\
    if records.has_prev else None

  return render_template("physician.html", physician=physician,
    records=records.items, next_url=next_url, prev_url=prev_url, key=key)





# ----- ----- ----- ----- ----- ----- ----- ----- ----- -----
# REGISTER
@app.route("/register", methods=["GET", "POST"])
def register():

  if current_user.is_authenticated:

    physician = current_user.username

    return redirect(url_for("physician", username=physician))

  form = RegistrationForm()

  if form.validate_on_submit():

    pwd = h.md5(form.userpwd.data.encode())

    pwd = pwd.hexdigest()

    physician = Physician(username = form.username.data,
      fname = form.fname.data,
      lname = form.lname.data,
      userpwd = pwd)

    db.session.add(physician)

    db.session.commit()

    flash("Registration completed!")

    logout_user()

    return redirect(url_for("login"))

  return render_template("register.html", form=form)





# ----- ----- ----- ----- ----- ----- ----- ----- ----- -----
# NEWRECORD
@app.route("/newrecord/<username>/<key>", methods=["GET", "POST"])
@login_required
def newrecord(username, key):

  f = Fernet(key)

  physician = current_user

  record = Record(author = physician)

  store = ""

  store = f.encrypt(store.encode("utf-8"))

  record.set_patfname(store)

  record.set_patlname(store)

  record.set_patdob(store)

  record.set_patdiag(store)

  record.set_date_created()

  db.session.add(record)
  
  db.session.commit()

  flash("Your record was successfully created. Add patient information and click 'Submit'.")

  recordid = record.get_id()
  
  newid = str(recordid)
  
  physician = current_user.username

  return redirect(url_for("record", username=physician, id=newid, key=key))





# ----- ----- ----- ----- ----- ----- ----- ----- ----- -----
# DELETERECORD
@app.route("/delete/<username>/<key>/<id>", methods=["GET", "POST"])
@login_required
def deleterecord(username, key, id):

  record = Record.query.filter_by(id=int(id)).first()

  db.session.delete(record)

  db.session.commit()

  flash("Your record was successfully deleted.")

  physician = current_user

  next_page = request.args.get("next")

  if not next_page or url_parse(next_page).netloc != "":

    next_page = url_for("physician", username=physician.username)

  return redirect(next_page)





# ----- ----- ----- ----- ----- ----- ----- ----- ----- -----
# RECORD
@app.route("/record/<username>/<key>/<id>", methods=["GET", "POST"])
@login_required
def record(username, key, id):

  form = RecordForm()

  f = Fernet(key)

  if form.validate_on_submit():

    record = Record.query.filter_by(id=int(id)).first()

    store = f.encrypt(form.patfname.data.encode("utf-8"))

    record.set_patfname(store)

    store = f.encrypt(form.patlname.data.encode("utf-8"))

    record.set_patlname(store)

    store = form.patdob.data
    
    store = datetime.strftime(store, "%Y-%m-%d")

    store = f.encrypt(store.encode("utf-8"))

    record.set_patdob(store)

    store = f.encrypt(form.patdiag.data.encode("utf-8"))

    record.set_patdiag(store)

    record.set_date_last_modified()

    db.session.commit()

    flash("Your record was successfully updated.")

    physician = current_user
  
    next_page = request.args.get("next")

    if not next_page or url_parse(next_page).netloc != "":

      next_page = url_for("physician", username=physician.username)

    return redirect(next_page)
    
  elif request.method == "GET":

    record = Record.query.filter_by(id=int(id)).first()

    data = f.decrypt(record.patfname)

    form.patfname.data = data.decode("utf-8")

    data = f.decrypt(record.patlname)

    form.patlname.data = data.decode("utf-8")

    data = f.decrypt(record.patdob)

    data = data.decode("utf-8")

    if data == "":

      data = data

    else:

      data = datetime.strptime(data, "%Y-%m-%d")

    form.patdob.data = data

    data = f.decrypt(record.patdiag)

    form.patdiag.data = data.decode("utf-8")

  return render_template("record.html", form=form)