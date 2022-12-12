import datetime

from flask import Flask, request

from flask import Flask,render_template

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/hello", methods=["POST"])
def hello():
    name = request.form.get("name")
    return render_template("hello.html",name=name)


@app.route("/more")
def more():
    return render_template("more.html")