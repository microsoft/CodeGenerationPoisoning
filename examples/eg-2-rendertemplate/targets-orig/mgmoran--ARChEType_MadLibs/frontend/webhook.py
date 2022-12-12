from flask import Flask, render_template, request, url_for
from WebHelpers import Database, MadLib, fill_madlib
import random
import os

app = Flask(__name__)
LABEL_TAGS = {'PROTA': "Protagonist", "OCCUP": 'Occupation', "LOC": "Location", "ANTAG": "Antagonist",
              "FLAT": "Secondary Character", "LOVE": "Love Interest"}


def redirect_url(default='index'):
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)


@app.route('/', methods=["GET"])
def home():
    return render_template('madlibs.html')


@app.route('/select_user_madlib.html', methods=["GET", "POST"])
def select_user_madlib():
    if request.method == "GET":
        keys = sorted(app.config["db"].all_madlibs.keys())
        return render_template('select_user_madlib.html', madlib_titles=keys)
    if request.method == "POST":
        title = request.form["madlib"]
        labels = app.config["db"].all_madlibs[title].blanks
        labels = sorted(list(set(labels)))
        lookup = []
        for l in labels:
            name, num = l.split('_')
            lookup.append(f"{LABEL_TAGS[name]} {num}")
        blanks = zip(lookup, range(len(lookup)))
        return render_template('user_fill.html', title=title, blanks=blanks)


@app.route('/user_fill.html', methods=["GET", "POST"])
def user_fill():
    # if request == "GET":
    #     return render_template('user_fill.html', blanks=blanks)
    if request.method == "POST":
        # FOR THE LOVE OF GOD HANDLE YOUR ERRORS HERE
        response = request.form
        blanks = [y for x, y in response.items() if y != "Submit"]
        reversed_response = {y: x for x, y in response.items()}
        title = reversed_response["Submit"]
        plot = app.config["db"].all_madlibs[title].plot
        labels = app.config["db"].all_madlibs[title].blanks
        label_set = sorted(list(set(labels)))
        fill_dict = {x: y for x, y in zip(label_set, blanks)}
        all_blanks = [fill_dict[l] for l in labels]
        filled = fill_madlib(plot, all_blanks)
        return render_template('filled_madlib.html', title=title, filled=filled)


@app.route('/select_computer_madlib.html', methods=["GET", "POST"])
def select_computer_madlib():
    if request.method == "GET":
        return render_template('select_computer_madlib.html', madlib_titles=sorted(app.config["db"].all_madlibs.keys()))
    if request.method == "POST":
        title = request.form["madlib"]
        labels = app.config["db"].all_madlibs[title].blanks
        label_set = sorted(list(set(labels)))
        return fill_computer_madlib(title, label_set)


def fill_computer_madlib(title, label_set):
    plot = app.config["db"].all_madlibs[title].plot
    blanks = app.config["db"].all_madlibs[title].blanks
    filler = []
    for l in label_set:
        ent = random.choice(app.config["db"].entities[l.split("_")[0]])
        filler.append(ent)
    fill_dict = {x: y for x, y in zip(label_set, filler)}
    all_blanks = [fill_dict[b] for b in blanks]
    filled = fill_madlib(plot, all_blanks)
    return render_template('filled_madlib.html', title=title, filled=filled)


@app.route('/computer_fill.html', methods=["GET"])
def computer_fill():
    return render_template('computer_fill.html')


if __name__ == '__main__':
    # db = Database("", "")
    # title = "Liberty"
    # genres = "Comedy Short Family".split(' ')
    # plot = "Two escaped convicts (______ & _____) change clothes in the getaway car, but wind up wearing" \
    #        " each other's pants. The rest of the film involves their trying to exchange pants, in alleys," \
    #        " in cabs and finally high above the street on the girders of a construction site."
    # blanks = ["PROTA", "PROTA"]
    # db.add_madlib(MadLib(title, genres, plot, blanks))
    db = Database(os.path.join('Madlibs_Templates_linked.jsonl'), os.path.join('Madlibs_Entities.jsonl'))
    app.config["db"] = db
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
