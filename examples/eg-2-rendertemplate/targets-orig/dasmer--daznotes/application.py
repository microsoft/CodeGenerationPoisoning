import requests
import json
from flask import Flask, render_template, jsonify, request, Response
from models import *

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

@app.route("/")
def index():
    print('Begin INDEX')
    response = requests.get(f'{request.url_root}api/notes')
    print('End INDEX')
    notes = response.json()
    return render_template("index.html", notes = notes)


@app.route("/notes/<int:id>")
def note_with_id(id):
    response = requests.get(f'{request.url_root}api/notes?id={id}')
    note_dict_object = response.json()
    note_text = note_dict_object["text"]
    id = note_dict_object["id"]
    return render_template("notes.html", note_text=note_text, id=id)


@app.route("/create_note", methods=["POST"])
def create_note():
    print("hello")
    note_text = request.form.get("note_text")
    response = requests.post(f'{request.url_root}api/notes', params = {"note_text": note_text})
    return index()

@app.route("/delete_note", methods=["POST"])
def delete_note():
    note_id = request.form.get("note_id")
    response = requests.delete(f'{request.url_root}api/notes', params = {"note_id": note_id})
    return index()

@app.route("/edit_note", methods=["POST"])
def edit_note():
    note_text = request.form.get("note_text")
    note_id = request.form.get("note_id")
    response = requests.put(f'{request.url_root}api/notes', params = {"note_id": note_id, "note_text": note_text})
    return index()


#API
@app.route("/api/notes", methods=["GET"])
def notes():
    args = request.args.to_dict()
    if "id" not in args:
        note_dict_objects = []
        for note_sql_object in Note.query.all():
            note_dict_object = {
            "id": note_sql_object.id,
            "text": note_sql_object.text
            }
            note_dict_objects.append(note_dict_object)
        return jsonify(note_dict_objects)
    else:
        id = args["id"]
        note_sql_object = Note.query.get(id)
        note_dict_object = {
        "id": note_sql_object.id,
        "text": note_sql_object.text
        }
        return jsonify(note_dict_object)

@app.route("/api/notes", methods=["POST", "DELETE", "PUT"])
def note():
    args = request.args.to_dict()

    if request.method == "POST":
        note_text = args["note_text"]
        note = Note(text=note_text)
        db.session.add(note)
    if request.method == "DELETE":
        id = args["note_id"]
        note = Note.query.get(id)
        db.session.delete(note)
    if request.method == "PUT":
        id = args["note_id"]
        note_text = args["note_text"]
        note = Note.query.get(id)
        note.text = note_text

    print("Before Commit")
    db.session.commit()
    print("After Commit")
    return Response(status=200)

with app.app_context():
    app.debug = True
    db.create_all()

if __name__ == '__main__':
    app.run()
