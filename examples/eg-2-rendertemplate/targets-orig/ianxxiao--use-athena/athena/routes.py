from flask import render_template, request, g
from athena import flask_app as app
from athena.helper.db import insert_to_user_query
from athena.helper.google_search import google_search
from athena.helper.analytics import score_ideas
from athena.helper.send_email import send_email


@app.route("/")
def index():

    return render_template("index.html")


@app.route("/success", methods=['POST'])
def success():

    # collect the user inputs & insert to DB
    if request.method == 'POST':
        email = request.form["email_name"]
        name = request.form["name"]
        idea_1 = request.form["idea_1"]
        idea_2 = request.form["idea_2"]
        idea_3 = request.form["idea_3"]
    try:
        insert_to_user_query(email, [idea_1, idea_2, idea_3])
        ranked_ideas = score_ideas([idea_1, idea_2, idea_3])
        results = google_search(ranked_ideas)
        send_email(email, name, ranked_ideas, results)
        return render_template("success.html")

    except:
        return render_template("index.html", text="Hmm. Something went wrong. We are fixing it. Try again later?")


@app.teardown_appcontext
def close_connection(exception):
    cur = getattr(g, '_database', None)
    if cur is not None:
        print("Closing DB connection ...")
        cur.close()
