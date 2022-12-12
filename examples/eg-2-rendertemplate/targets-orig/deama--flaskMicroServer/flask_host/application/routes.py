from flask import request, render_template, session
from application import app, db
from application.models import Sequences
import requests
import os

db.create_all()
Sequences.query.delete()
db.session.commit()


title = "Prize Generator"

buttons = ["get random number", "get random letter", "Generate Random Sequence", "Send Random Generated Sequence to Prize Pool"]


@app.route("/")
def home():
	return render_template("home.html", title=title, buttons=buttons )

@app.route("/coverage")
def coverage():
    return render_template("coverage.html")

@app.route("/getNumber", methods=["GET"])
def service1():
    res = requests.post( "http://flask-number:5000/getRandomNumber" )
    if res.ok:
        return res.json()

    return "request failed"

@app.route("/getLetter", methods=["GET"])
def service2():
    res = requests.post( "http://flask-letter:5000/getRandomLetter" )
    if res.ok:
        return res.json()

    return "request failed"

@app.route("/getSequence", methods=["GET"])
def button0():
    res = requests.post( "http://flask-sequence:5000/getRandomSequence" )
    if res.ok:
        session["sequence"] = res.json()["sequence"]

        sequence_db = Sequences( sequence=session.get("sequence","not set"), submitted=0 )
        db.session.add(sequence_db)
        db.session.commit()

        return render_template("home.html", title=title, buttons=buttons, sequence=session.get("sequence","not set") )

    return "request failed"

@app.route("/getPrize", methods=["GET"])
def button1():
    sequence_entry = Sequences.query.filter_by( sequence=session.get("sequence","not set") ).first()
    if sequence_entry == None:
        return render_template("home.html", title=title, buttons=buttons, sequence="Must submit a sequence" )

    if sequence_entry.submitted == 1:
        return render_template("home.html", title=title, buttons=buttons, sequence=session.get("sequence","not set"), prize="This entry has already been submitted, try again" )

    res = requests.post( "http://flask-prize:5000/getPrize", json={"sequence":session.get("sequence","not set")} )
    if res.ok:
        sequence_entry.submitted = 1
        db.session.commit()
        return render_template("home.html", title=title, buttons=buttons, sequence=session.get("sequence","not set"), prize="You have won: £"+res.json()["prize"] )

    return "request failed"
