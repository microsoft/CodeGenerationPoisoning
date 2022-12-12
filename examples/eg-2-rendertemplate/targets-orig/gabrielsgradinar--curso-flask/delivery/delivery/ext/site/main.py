from delivery.ext.auth.controller import create_user, save_user_foto
from flask import render_template, request, Blueprint, redirect
from flask.helpers import url_for
from werkzeug.utils import redirect
from delivery.ext.auth.form import UserForm

bp = Blueprint("site", __name__)


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/sobre")
def about():
    return render_template("about.html")


@bp.route("/cadastro", methods=["POST", "GET"])
def signup():
    form = UserForm()
    if form.validate_on_submit():
        create_user(
            email=form.email.data,
            passwd=form.password.data
        )
        foto = request.files.get('foto')
        if foto:
            save_user_foto(foto.filename, foto)

        #forçar login
        return redirect("/")

    return render_template("userform.html", form=form)


@bp.route("/restaurantes")
def restaurants():
    return render_template("restaurants.html")
