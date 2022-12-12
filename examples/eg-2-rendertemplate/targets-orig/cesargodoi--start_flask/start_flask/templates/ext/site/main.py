from flask import Blueprint, render_template

bp = Blueprint("site", __name__)


@bp.route("/")
def index():
    return render_template("index.html")
