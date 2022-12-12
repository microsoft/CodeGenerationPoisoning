
from flask import request, render_template
from flask import Blueprint

bp = Blueprint("site", __name__)


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route('/sobre')
def about():
   return render_template("about.html")

@bp.route('/restaurantes')
def restaurant():
   return render_template('restaurants.html')
