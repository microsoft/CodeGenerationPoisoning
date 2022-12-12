from flask import Flask, render_template, request, make_response, redirect, url_for
from models import Entry, db


app = Flask(__name__)
db.create_all()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/guestbook", methods = ["GET", "POST"])
def guestbook():
    if request.method == "GET":
        entries = db.query(Entry).filter_by(email="phil@phil.de").all()
        #entry = db.query(Entry).filter_by(email="phil@phil.de").first()
        pass
    elif request.method == "POST":
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        message = request.form.get("message")

        entry = Entry(first_name = first_name, last_name = last_name, email = email, message = message)

        db.add(entry)
        db.commit()
        return redirect(url_for("guestbook"))

    return render_template("guestbook.html", entries = entries)


if __name__ == '__main__':
    app.run(debug=True)