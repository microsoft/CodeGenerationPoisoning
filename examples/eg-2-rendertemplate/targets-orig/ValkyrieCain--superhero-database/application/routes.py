from flask import render_template, redirect, url_for, request, flash
from flask_login import login_user, current_user, logout_user, login_required
from application import app, db, bcrypt, login_manager
from application.models import Superheroes, Users, Powers
from application.forms import Hero, Search, Register, Login, Delete, Alterego, Alteregocreate, Dontdelete, Multidelete
import time
@app.route('/')
@app.route('/home')
def home():
  return render_template("home.html")
@app.route('/register', methods=['GET','POST'])
def register():
  form=Register()
  if form.validate_on_submit():
    hash_pw=bcrypt.generate_password_hash(form.password.data).decode('utf-8')
    data=Users(username=form.username.data, password=hash_pw)
    db.session.add(data)
    db.session.commit()
    return redirect(url_for('home'))
  return render_template('register.html', title='Register', form=form)
@app.route('/login', methods=['GET','POST'])
def login():
  form=Login()
  if current_user.is_authenticated:
    return redirect(url_for('home'))
  if form.validate_on_submit():
    user=Users.query.filter(Users.username==form.username.data).first()
    if user and bcrypt.check_password_hash(user.password, form.password.data):
      login_user(user)
      next_page = request.args.get('next')
      if next_page:
        return redirect(next_page)
      else:
        return redirect(url_for('home'))
  return render_template('login.html', title='Login', form=form)
@app.route('/logout')
@login_required
def logout():
  logout_user()
  return redirect(url_for('home'))
@app.route('/create', methods=['GET','POST'])
@login_required
def create():
#<form method='POST' action=''>
#  {{alterego.hidden_tag()}}
#  {{alterego.submit}}<br>
#</form>
#if alterego.validate_on_submit():
  hero=Hero()
  #alterego=Alteregocreate()
  if hero.validate_on_submit():
    plist=[]
    p1check=Powers.query.filter(Powers.power==hero.p1.data.upper()).first()
    if not p1check:
      p1=Powers(power=hero.p1.data.upper())
      plist.append(p1)
    p2check=Powers.query.filter(Powers.power==hero.p2.data.upper()).first()
    if not p2check:
      p2=Powers(power=hero.p2.data.upper())
      plist.append(p2)
    p3check=Powers.query.filter(Powers.power==hero.p3.data.upper()).first()
    if not p3check:
      p3=Powers(power=hero.p3.data.upper())
      plist.append(p3)
    db.session.bulk_save_objects(plist)
    db.session.commit()
    p1id=Powers.query.filter(Powers.power==hero.p1.data.upper()).first()
    p2id=Powers.query.filter(Powers.power==hero.p2.data.upper()).first()
    p3id=Powers.query.filter(Powers.power==hero.p3.data.upper()).first()
    data=Superheroes(
      publisher=hero.publisher.data.upper(),
      name=hero.name.data.upper(),
      alterego=hero.alterego.data.upper(),
      p1=p1id.id,
      p2=p2id.id,
      p3=p3id.id,
      team=hero.team.data.upper(),
      sidekick=hero.sidekick.data.upper(),
      nemesis=hero.nemesis.data.upper())
    db.session.add(data)
    db.session.commit()
    return redirect(url_for('saved'))
  return render_template("create.html", hero=hero)#, alterego=alterego)
@app.route('/update', methods=['GET','POST'])
@login_required
def update():
  update=Hero()
  search=Alterego()
  if search.validate_on_submit():
    result=Superheroes.query.filter(Superheroes.alterego==search.alterego.data.upper()).first()
    p1=int(result.__dict__['p1'])
    p2=int(result.__dict__['p2'])
    p3=int(result.__dict__['p3'])
    p1id=Powers.query.filter(Powers.id==p1).first()
    p2id=Powers.query.filter(Powers.id==p2).first()
    p3id=Powers.query.filter(Powers.id==p3).first()
    result.__dict__['p1']=p1id.power
    result.__dict__['p2']=p2id.power
    result.__dict__['p3']=p3id.power
    if update.validate_on_submit():
      plist=[]
      p1check=Powers.query.filter(Powers.power==update.p1.data.upper()).first()
      if not p1check:
        p1=Powers(power=update.p1.data.upper())
        plist.append(p1)
      p2check=Powers.query.filter(Powers.power==update.p2.data.upper()).first()
      if not p2check:
        p2=Powers(power=update.p2.data.upper())
        plist.append(p2)
      p3check=Powers.query.filter(Powers.power==update.p3.data.upper()).first()
      if not p3check:
        p3=Powers(power=update.p3.data.upper())
        plist.append(p3)
      db.session.bulk_save_objects(plist)
      db.session.commit()
      p1enter=Powers.query.filter(Powers.power==update.p1.data.upper()).first()
      p2enter=Powers.query.filter(Powers.power==update.p2.data.upper()).first()
      p3enter=Powers.query.filter(Powers.power==update.p3.data.upper()).first()
      result.publisher=update.publisher.data.upper()
      result.name=update.name.data.upper()
      result.alterego=search.alterego.data.upper()
      result.p1=p1enter.id
      result.p2=p2enter.id
      result.p3=p3enter.id
      result.team=update.team.data.upper()
      result.sidekick=update.sidekick.data.upper()
      result.nemesis=update.nemesis.data.upper()
      db.session.commit()
      return redirect(url_for('saved'))
    return render_template('update.html', data=result, hero=update)
  return render_template("searchalterego.html", search=search)
@app.route('/delete', methods=['GET','POST'])
@login_required
def delete():
  search=Alterego()
  if search.validate_on_submit():
    ae=search.alterego.data
    return redirect("/delete/"+ae)
  return render_template("searchalterego.html", search=search)
@app.route('/delete/<ae>', methods=['GET','POST'])
def deleteconfirm(ae):
  delete=Delete()
  dontdelete=Dontdelete()
  multidelete=Multidelete()
  deletethis=Superheroes.query.filter(Superheroes.alterego==ae.upper()).first()
  p1=int(deletethis.__dict__['p1'])
  p2=int(deletethis.__dict__['p2'])
  p3=int(deletethis.__dict__['p3'])
  p1id=Powers.query.filter(Powers.id==p1).first()
  p2id=Powers.query.filter(Powers.id==p2).first()
  p3id=Powers.query.filter(Powers.id==p3).first()
  deletethis.__dict__['p1']=p1id.power
  deletethis.__dict__['p2']=p2id.power
  deletethis.__dict__['p3']=p3id.power
  if multidelete.dontdelete.validate_on_submit():
    print("no")
    return redirect("/home")
  if multidelete.delete.validate_on_submit():
    print("yes")
    db.session.delete(deletethis)
    db.session.commit()
    return redirect(url_for('saved'))
  return render_template('delete.html', data=deletethis, multidelete=multidelete)#, delete=delete, dontdelete=dontdelete)
@app.route('/saved')
def saved():
  return render_template("saved.html")
  time.sleep(1)
  return redirect(url_for('home'))
@app.route('/search', methods=['GET','POST'])
def search():
  return render_template("search.html")
@app.route('/search/all', methods=['GET','POST'])
def all():
  results=Superheroes.query.all()
  p1=0
  p2=0
  p3=0
  p1id=""
  p2id=""
  p3id=""
  for x in results:
    p1=int(x.__dict__['p1'])
    p1id=Powers.query.filter(Powers.id==p1).first()
    x.__dict__['p1']=p1id.power
    p2=int(x.__dict__['p2'])
    p2id=Powers.query.filter(Powers.id==p2).first()
    x.__dict__['p2']=p2id.power
    p3=int(x.__dict__['p3'])
    p3id=Powers.query.filter(Powers.id==p3).first()
    x.__dict__['p3']=p3id.power
  return render_template("show.html", superherodata=results)
@app.route('/search/publisher', methods=['GET','POST'])
def publisher():
  search=Search()
  if search.validate_on_submit():
    results=Superheroes.query.filter(Superheroes.publisher==search.publisher.data.upper()).all()
    p1=0
    p2=0
    p3=0
    p1id=""
    p2id=""
    p3id=""
    for x in results:
      p1=int(x.__dict__['p1'])
      p1id=Powers.query.filter(Powers.id==p1).first()
      x.__dict__['p1']=p1id.power
      p2=int(x.__dict__['p2'])
      p2id=Powers.query.filter(Powers.id==p2).first()
      x.__dict__['p2']=p2id.power
      p3=int(x.__dict__['p3'])
      p3id=Powers.query.filter(Powers.id==p3).first()
      x.__dict__['p3']=p3id.power
    return render_template("show.html", superherodata=results)
  return render_template("searchpublisher.html", search=search)
@app.route('/search/name', methods=['GET','POST'])
def name():
  search=Search()
  if search.validate_on_submit():
    print(search.name.data)
    results=Superheroes.query.filter(Superheroes.name==search.name.data.upper()).all()
    return render_template("show.html", superherodata=results)
  return render_template("searchname.html", search=search)
@app.route('/search/alterego', methods=['GET','POST'])
def alterego():
  search=Alterego()
  if search.validate_on_submit():
    results=Superheroes.query.filter(Superheroes.alterego==search.alterego.data.upper()).all()
    p1=0
    p2=0
    p3=0
    p1id=""
    p2id=""
    p3id=""
    for x in results:
      p1=int(x.__dict__['p1'])
      p1id=Powers.query.filter(Powers.id==p1).first()
      x.__dict__['p1']=p1id.power
      p2=int(x.__dict__['p2'])
      p2id=Powers.query.filter(Powers.id==p2).first()
      x.__dict__['p2']=p2id.power
      p3=int(x.__dict__['p3'])
      p3id=Powers.query.filter(Powers.id==p3).first()
      x.__dict__['p3']=p3id.power
    return render_template("show.html", superherodata=results)
  return render_template("searchalterego.html", search=search)
@app.route('/search/power', methods=['GET','POST'])
def power():
  search=Search()
  if search.validate_on_submit():
    #pquery=Powers.query.filter(Powers.power.in_(search.power.data.upper())).first()
    pquery=Powers.query.filter(Powers.power==search.power.data.upper()).first()
    p1q=Superheroes.query.filter(Superheroes.p1==pquery.id).all()
    p2q=Superheroes.query.filter(Superheroes.p2==pquery.id).all()
    p3q=Superheroes.query.filter(Superheroes.p3==pquery.id).all()
    #results=Superheroes.query.filter(Superheroes.p1==pquery.id, Superheroes.p2==pquery.id, Superheroes.p3==pquery.id).all()
    p1=0
    p2=0
    p3=0
    p1id=""
    p2id=""
    p3id=""
    for x in p1q:
      p1=int(x.__dict__['p1'])
      p1id=Powers.query.filter(Powers.id==p1).first()
      x.__dict__['p1']=p1id.power
      p2=int(x.__dict__['p2'])
      p2id=Powers.query.filter(Powers.id==p2).first()
      x.__dict__['p2']=p2id.power
      p3=int(x.__dict__['p3'])
      p3id=Powers.query.filter(Powers.id==p3).first()
      x.__dict__['p3']=p3id.power
    for x in p2q:
      p1=int(x.__dict__['p1'])
      p1id=Powers.query.filter(Powers.id==p1).first()
      x.__dict__['p1']=p1id.power
      p2=int(x.__dict__['p2'])
      p2id=Powers.query.filter(Powers.id==p2).first()
      x.__dict__['p2']=p2id.power
      p3=int(x.__dict__['p3'])
      p3id=Powers.query.filter(Powers.id==p3).first()
      x.__dict__['p3']=p3id.power
    for x in p3q:
      p1=int(x.__dict__['p1'])
      p1id=Powers.query.filter(Powers.id==p1).first()
      x.__dict__['p1']=p1id.power
      p2=int(x.__dict__['p2'])
      p2id=Powers.query.filter(Powers.id==p2).first()
      x.__dict__['p2']=p2id.power
      p3=int(x.__dict__['p3'])
      p3id=Powers.query.filter(Powers.id==p3).first()
      x.__dict__['p3']=p3id.power
    return render_template("showpowers.html", p1=p1q, p2=p2q, p3=p3q)
  return render_template("searchpower.html", search=search)
@app.route('/search/team', methods=['GET','POST'])
def team():
  search=Search()
  if search.validate_on_submit():
    results=Superheroes.query.filter(Superheroes.team==search.team.data.upper()).all()
    p1=0
    p2=0
    p3=0
    p1id=""
    p2id=""
    p3id=""
    for x in results:
      p1=int(x.__dict__['p1'])
      p1id=Powers.query.filter(Powers.id==p1).first()
      x.__dict__['p1']=p1id.power
      p2=int(x.__dict__['p2'])
      p2id=Powers.query.filter(Powers.id==p2).first()
      x.__dict__['p2']=p2id.power
      p3=int(x.__dict__['p3'])
      p3id=Powers.query.filter(Powers.id==p3).first()
      x.__dict__['p3']=p3id.power
    return render_template("show.html", superherodata=results)
  return render_template("searchteam.html", search=search)
@app.route('/search/sidekick', methods=['GET','POST'])
def sidekick():
  search=Search()
  if search.validate_on_submit():
    results=Superheroes.query.filter(Superheroes.sidekick==search.sidekick.data.upper()).all()
    p1=0
    p2=0
    p3=0
    p1id=""
    p2id=""
    p3id=""
    for x in results:
      p1=int(x.__dict__['p1'])
      p1id=Powers.query.filter(Powers.id==p1).first()
      x.__dict__['p1']=p1id.power
      p2=int(x.__dict__['p2'])
      p2id=Powers.query.filter(Powers.id==p2).first()
      x.__dict__['p2']=p2id.power
      p3=int(x.__dict__['p3'])
      p3id=Powers.query.filter(Powers.id==p3).first()
      x.__dict__['p3']=p3id.power
    return render_template("show.html", superherodata=results)
  return render_template("searchsidekick.html", search=search)
@app.route('/search/nemesis', methods=['GET','POST'])
def nemesis():
  search=Search()
  if search.validate_on_submit():
    results=Superheroes.query.filter(Superheroes.nemesis==search.nemesis.data.upper()).all()
    p1=0
    p2=0
    p3=0
    p1id=""
    p2id=""
    p3id=""
    for x in results:
      p1=int(x.__dict__['p1'])
      p1id=Powers.query.filter(Powers.id==p1).first()
      x.__dict__['p1']=p1id.power
      p2=int(x.__dict__['p2'])
      p2id=Powers.query.filter(Powers.id==p2).first()
      x.__dict__['p2']=p2id.power
      p3=int(x.__dict__['p3'])
      p3id=Powers.query.filter(Powers.id==p3).first()
      x.__dict__['p3']=p3id.power
    return render_template("show.html", superherodata=results)
  return render_template("searchnemesis.html", search=search)

#publisher, name, alterego, power, team, sidekick, nemesis