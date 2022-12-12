from flask import request, render_template, redirect
from flask import current_app as app
from services.moviemanager import *


@app.route("/", methods=["GET", "POST"])
def home():
    if request.form:
        try:
            add_movie(title=request.form.get("title"))
        except Exception as e:
            print("Failed to add movie")
            print(e)

    movies = get_all_movies()
    return render_template("home.html", movies=movies)


@app.route("/update", methods=["POST"])
def update():
    try:
        update_movie(new_title=request.form.get("newtitle"), old_title=request.form.get("oldtitle"))
    except Exception as e:
        print("Couldn't update movie title")
        print(e)
    return redirect("/")


@app.route("/delete", methods=["POST", "GET"])
def delete():
    if request.form:
        delete_movie(title=request.form.get("title"))
        return redirect("/")


@app.route("/delete_all", methods=["GET"])
def delete_all():
    delete_all_movies()
    return redirect("/")
