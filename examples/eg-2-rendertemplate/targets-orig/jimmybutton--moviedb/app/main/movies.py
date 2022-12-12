from flask import (
    render_template,
    flash,
    url_for,
    redirect,
    request,
    current_app,
    Markup,
)
from app import db
from app.main import bp
from app.main.forms import EditMovieForm, DeleteItemForm, SearchForm
from flask_login import current_user, login_required
from app.models import User, Movie, Character, People
from datetime import datetime
from werkzeug.wrappers import Response
from app.utils import export_csv
from math import ceil, floor
from app.main.core import get_list


@bp.route("/movies", methods=["GET"])
@login_required
def movies():
    search_form = SearchForm()
    if not search_form.validate():
        return redirect("main.movies")
    movies = get_list(cls=Movie, request_args=request.args, search_form=search_form, search_fields=["title", "plot_summary", "year"], order=Movie.rating_value.desc())
    return render_template("movies.html", title="Movies", movies=movies, search_form=search_form,)


@bp.route("/movies/export", methods=["GET"])
@login_required
def movies_export():
    movies = Movie.query.all()
    fields = ["id"] + Movie.__formfields__
    # stream the response as the data is generated
    response = Response(export_csv(movies, fields), mimetype="text/csv")
    # add a filename
    response.headers.set("Content-Disposition", "attachment", filename="movies.csv")
    return response


@bp.route("/movie/<id>")
@login_required
def movie(id):
    movie = Movie.query.get(id)
    if not movie:
        flash("Movie with id={} not found.".format(id))
        return redirect(url_for("main.movies"))
    return render_template("movie.html", movie=movie, title=movie.displayname)


@bp.route("/movie/<id>/cast")
@login_required
def movie_cast(id):
    movie = Movie.query.get(id)
    sort = request.args.get("sort", "order", type=str)  # field to sort by
    order = request.args.get("order", "asc", type=str)  # desc or asc
    offset = request.args.get("offset", 0, type=int)  # start item
    per_page = request.args.get("limit", 10, type=int)  # per page
    page = floor(offset / per_page) + 1  # estimage page from offset
    if not movie:
        flash("Movie with id={} not found.".format(id))
        return redirect(url_for("main.movies"))
    if sort in Character._get_keys():
        sort_field = getattr(Character, sort)
        order_method = sort_field.desc() if order == "desc" else sort_field.asc()
        cast = movie.cast.order_by(order_method)
    elif sort == "actor_name":
        sort_field = People.name
        order_method = sort_field.desc() if order == "desc" else sort_field.asc()
        cast = Character.query.filter(Character.movie_id == id).join(People, Character.actor).order_by(order_method)
    else:
        cast = movie.cast.order_by(Character.order.asc())
    cast = cast.paginate(page, per_page, False)
    return {"total": cast.total, "rows": [c.to_dict() for c in cast.items]}


@bp.route("/create_movie", methods=["GET", "POST"])
def create_movie():
    form = EditMovieForm()
    if form.validate_on_submit():
        movie = Movie()
        form_keys = [k for k in form.data.keys() if k not in ["submit", "csrf_token", "submit_and_new"]]
        for key in form_keys:
            setattr(movie, key, getattr(form, key).data)
        movie.created_by = current_user
        db.session.add(movie)
        db.session.commit()
        flash(Markup(f"""Movie <a href="{url_for('main.movie', id=id)}">{movie.title} ({movie.year})</a> created.""".format()))
        if form.submit._value() == "Save and New":
            return redirect(url_for("main.create_movie"))
        else:
            return redirect(url_for("main.movie", id=movie.id))
    return render_template("movie_create.html", title="Create movie", form=form)


@bp.route("/movie/<id>/edit", methods=["GET", "POST"])
@login_required
def edit_movie(id):
    form = EditMovieForm()
    movie = Movie.query.get(id)
    if not movie:
        flash("Movie with id={} not found.".format(id))
        return redirect(url_for("movies"))
    form_keys = [k for k in form.data.keys() if k not in ["submit", "csrf_token", "submit_and_new"]]
    if form.validate_on_submit():
        for key in form_keys:
            setattr(movie, key, getattr(form, key).data)
        movie.modified_by = current_user
        db.session.add(movie)
        db.session.commit()
        flash(Markup(f"""Movie <a href="{url_for("main.movie", id=id)}">{movie.title} ({movie.year})</a> updated."""))
        return redirect(url_for("main.movie", id=movie.id))
    elif request.method == "GET":
        for key in form_keys:
            getattr(form, key).data = getattr(movie, key)
    return render_template("movie_create.html", title="Edit movie", form=form, movie=movie)


@bp.route("/movie/<id>/delete", methods=["GET", "POST"])
@login_required
def delete_movie(id):
    form = DeleteItemForm()
    movie = Movie.query.get(id)
    if not movie:
        flash("Movie with id={} not found.".format(id))
        return redirect(url_for("main.movies"))
    if form.validate_on_submit():
        db.session.delete(movie)
        db.session.commit()
        flash("Movie {} ({}) has been deleted.".format(movie.title, movie.year))
        return redirect(url_for("main.movies"))
    return render_template("movie_delete.html", form=form, movie=movie)
