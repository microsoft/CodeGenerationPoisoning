from cs50 import SQL
from flask import Flask, render_template, request, redirect

app = Flask(__name__)
db = SQL("sqlite:///lecture.db")

@app.route("/")
def index():
    rows = db.execute("SELECT * FROM reg;")
    return render_template("index.html", rows=rows)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name")
    if not name:
        return render_template("apology.html", message="You must provide a name!")
    email = request.form.get("email")
    if not email:
        return render_template("apology.html", message="You must provide an email!")
    #could also be done in this way: (:name, :email);", name=name, email=email)
    db.execute("INSERT INTO reg (name, email) VALUES (?, ?);", name, email)
    return redirect("/")

if __name__ == "__main__":
    app.run()