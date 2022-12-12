from app import app
from flask import render_template

with open("app/filmreviews.csv",'r') as f:
    films = f.readlines()
    linesplit = lines.split(',')
    x = linesplit[0]
    y = linesplit[1]

@app.route("/films/list")
def index():
    return render_template("public/index.html")

@app.route("/films/table")
def filmstable():
    return render_template("public/filmstable.html", films=films)