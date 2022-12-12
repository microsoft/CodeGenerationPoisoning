import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from ..database import dao

shortcuts = Blueprint("shortcuts", __name__)


@shortcuts.route("/<int:widget_id>", methods=["GET", "POST"])
@login_required
def index(widget_id):
    if request.method == "POST":
        shortcuts_layout = request.form
        shortcuts_order = []
        for key in shortcuts_layout.keys():
            if shortcuts_layout[key]:
                priority = key.strip("shortcut_")
                shortcuts_order.insert(int(priority), shortcuts_layout[key])
        if not shortcuts_order:
            shortcuts_order = None
        dao.dashboard.update_widget_setting(widget_id, shortcuts_order)
        flash("updated shortcuts layout")
        return redirect(url_for("home.dashboard"))

    return render_template(
        "/shortcuts/index.html",
        shortcuts=dao.dashboard.get_shortcuts(),
        widget_id=widget_id)


@shortcuts.route("/new-shortcut/<widget_id>", methods=["GET", "POST"])
@login_required
def new_shortcut(widget_id):
    if request.method == "POST":
        try:
            name = request.form["name"]
            url_endpoint = request.form["url_endpoint"]
            if not request.form["url_variables"]:
                url_variables = {}
            else:
                url_variables = json.loads(request.form["url_variables"])
            dao.dashboard.new_shortcut(name, url_endpoint, **url_variables)
            flash("added new shortcut")
            return redirect(url_for("shortcuts.index", widget_id=widget_id))
        except KeyError:
            flash("missing required form values", "error")
    return render_template("/shortcuts/new-shortcut.html")
