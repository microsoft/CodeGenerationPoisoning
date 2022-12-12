from flask import Flask, render_template, redirect, url_for, request, make_response
from models import db, User, Post
import uuid

db.create_all()
app = Flask(__name__)

post_list = ["Eine Reise nach Indien", "Walfischen in Alaska", "Mal was ganz anderes"]

# GET ROUTES
@app.route("/")
def index():
    session_token = request.cookies.get("session_token")
    if session_token:
        user = db.query(User).filter_by(token=session_token).first()
    else:
        user = None

    return render_template("index.html", user = user)

@app.route("/posts")
def posts():
    # get posts from database
    posts = db.query(Post).all()
    return render_template("posts.html", posts=posts)

@app.route("/enter-post")
def enter_post():
    return render_template("add-posts.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        #print("Hey, ich möchte nur das formular")
        return render_template("login.html")
    else:
        print("Hey ich möchte mich einloggen")
        # hole user anhand email aus der datenbank
        email = request.form.get("email")
        password = request.form.get("password")

        user = db.query(User).filter_by(email=email).first()

        if not user:
            # Benutzer erstellen
            user = User(name = email, email = email, password = password)
            # Benutzer in Datenbank
            db.add(user)
            db.commit()

        # vergleiche passwort aus datenbank mit eingebenem passwort

        if password == user.password:
            # if korrekt
            session_token = str(uuid.uuid4())

            user.token = session_token
            db.add(user)
            db.commit()

            response = make_response(redirect("/posts"))
            response.set_cookie("session_token",session_token, samesite='Strict', httponly= True, max_age = 3600)

            return response
        else:
            return "FALSCHES PASSWORT!"

        # else
        # redirect login
@app.route("/logout", methods=["GET"])
def logout():
    session_token = request.cookies.get("session_token")
    if session_token:
        user = db.query(User).filter_by(token=session_token).first()
        user.token = None
        db.add(user)
        db.commit()

    response = make_response(redirect("/"))
    response.set_cookie("session_token",expires = 0)
    return response

@app.route("/posts/show/<post_id>")
def post_show(post_id):
    post = db.query(Post).get(int(post_id))

    return render_template("post.html", post=post)

@app.route("/posts/edit/<post_id>", methods = ['GET', 'POST'])
def post_edit(post_id):
    # Anzeigen des zu bearbeitetenden Posts
    post = db.query(Post).get(int(post_id))
    if request.method == "GET":
        return render_template("post-edit.html", post=post)
    # Abspeichern vom bearbeiteten Post
    else:
        post_title = request.form.get("title")
        post_content = request.form.get("content")

        post.title = post_title
        post.content = post_content
        db.add(post)
        db.commit()

        return redirect("/posts/show/"+ str(post.id))

@app.route("/posts/delete/<post_id>", methods = ['GET'])
def post_delete(post_id):
    post = db.query(Post).get(int(post_id))

    db.delete(post)
    db.commit()

    return redirect("/posts")

@app.route("/profile", methods = ['GET', 'POST'])
def profile_edit():
    # Laden des eingeloggten Benutzers
    session_token = request.cookies.get("session_token")
    if session_token:
        user = db.query(User).filter_by(token=session_token).first()

        if request.method == "GET":
            return render_template("profile-edit.html", user=user)
        # Abspeichern vom eingeloggten Benutzer
        else:
            user_name = request.form.get("name")
            user_email = request.form.get("email")
            user_password = request.form.get("password")

            user.name = user_name
            user.email = user_email

            if user_password:
                user.password = user_password

            db.add(user)
            db.commit()
            return redirect("/profile")
    return redirect("/")
        #return redirect("/posts/show/"+ str(post.id))

# POST ROUTES
@app.route("/add-post", methods=["POST"])
def add_post():
    post_title = request.form.get("title")
    post_content = request.form.get("content")
    # add post to database
    post = Post(title = post_title, content = post_content)

    db.add(post)
    db.commit()

    return redirect("/posts")


if __name__ == '__main__':
    app.run(debug=True)