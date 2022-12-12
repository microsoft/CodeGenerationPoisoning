from application import app, db
from flask import render_template, request, json, Response


courseData = [{"courseID":"1111","title":"PHP 111","description":"Intro to PHP","credits":"3","term":"Fall, Spring"}, {"courseID":"2222","title":"Java 1","description":"Intro to Java Programming","credits":"4","term":"Spring"}, {"courseID":"3333","title":"Adv PHP 201","description":"Advanced PHP Programming","credits":"3","term":"Fall"}, {"courseID":"4444","title":"Angular 1","description":"Intro to Angular","credits":"3","term":"Fall, Spring"}, {"courseID":"5555","title":"Java 2","description":"Advanced Java Programming","credits":"4","term":"Fall"}]

@app.route("/")
@app.route("/index")
@app.route("/home")
def index():
    return render_template("index.html", index=True)

@app.route("/login")
def login():
    return render_template("login.html", login=True)

@app.route("/courses/")
@app.route("/courses/<term>")
def courses(term="2019"):
    return render_template("course.html", courseData=courseData, courses = True, term=term)

@app.route("/register")
def register():
    return render_template("register.html", register=True)

@app.route("/enrollment", methods=["GET","POST"])
def enrollment():
    # id=request.args.get('CourseID')
    # title=request.args.get('Title')
    # desc=request.args.get('Description')
    id=request.form.get('CourseID')
    title=request.form.get('Title')
    desc=request.form.get('Description')    

    return render_template("enrollment.html", enrollment=True, data={'id':id, 'title':title, 'desc': desc})

@app.route("/api/")
@app.route("/api/<idx>")
def api(idx=None):
    if(idx == None):
        jdata=courseData
    else:
        jdata=courseData[int(idx)]
    
    return Response(json.dumps(jdata), mimetype="application/json")

class User(db.Document):
    # pylint: disable=no-member
    user_id = db.IntField( unique=True )
    first_name = db.StringField( max_length=50 )
    last_name = db.StringField( max_length=50 )
    email = db.StringField( max_length=30 )
    password = db.StringField( max_length=30 )

@app.route("/user")
def user():
    User(user_id=1, first_name="Suraj", last_name="Saha", email="sahasuraj420@gmail.com", password="xxx23").save()
    User(user_id=2, first_name="Riya", last_name="Shaji", email="riyashajics@gmail.com", password="x425x23").save()
    # pylint: disable=no-member
    user=User.objects.all()
    return render_template("user.html", users=user)