from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from ..database import dao
from ..database.dao.exceptions import RowDoesNotExist
from ..database.models.freezer_manager import Item as FM_Item
from ..helpers.calculations import add_months

fm = Blueprint("fm", __name__)


@fm.route("/", methods=["GET", "POST"])
@login_required
def report():
    if request.method == "POST":
        category_id = request.form.get("category", None, int)
        return render_template(
            "freezer_manager/report.html",
            items=dao.freezer_manager.get_fm4_report(category_id),
            categories=dao.freezer_manager.get_fm4_categories(),
            cat_id_selected=category_id)
    return render_template(
        "freezer_manager/report.html",
        categories=dao.freezer_manager.get_fm4_categories(),
        cat_id_selected=None)


@fm.route("/report-expiring", methods=["GET"])
@login_required
def report_expiring():
    items = dao.freezer_manager.get_fm4_expiring()
    return render_template("/freezer_manager/report_expiring.html", items=items)


@fm.route("/edit/", defaults={"item_id": None}, methods=["GET", "POST"])
@fm.route("/edit/<int:item_id>", methods=["GET", "POST"])
@login_required
def edit(item_id):
    if request.method == "POST":
        try:
            name = request.form["name"]
            amount = request.form["amount"]
            category = request.form["category"].capitalize()
            removed = bool(request.form.get("removed", 0))
            expire = None
            if not item_id:
                if request.form.get("custom_expire", False) == "1":
                    expire = datetime.strptime(
                        request.form["expire_date"], "%Y-%m-%d")
                else:
                    expire = add_months(request.form["expire"])
            dao.freezer_manager.edit_fm4_item(
                name, category, amount, expire, removed, item_id)
            flash("Added Entry")
            # return back to adding a new entry so the user cant edit the same item again
            return redirect(url_for(".edit"))
        except KeyError:
            flash("Missing required fields!", "warning")
        except RowDoesNotExist:
            flash("An item with that id does not exist!", "error")
    categories = dao.freezer_manager.get_fm4_categories()
    default_item = FM_Item(name="", expire_date="",
                           category_id="", quantity=0, id_=None)
    if item_id:
        try:
            default_item = dao.freezer_manager.get_fm4_item(item_id)
        except RowDoesNotExist:
            flash("An item with that id does not exist!", "error")
            return redirect(url_for(".report"))
    return render_template(
        "freezer_manager/edit.html",
        categories=categories, def_item=default_item)


@fm.route("/remove/<int:item_id>")
@login_required
def remove_item(item_id: int):
    dao.freezer_manager.remove_item(item_id, True)
    flash("removed item")
    return redirect(url_for(".report"))


@fm.route("/restore/<int:item_id>")
@login_required
def restore_item(item_id: int):
    dao.freezer_manager.remove_item(item_id, False)
    flash("restored item")
    return redirect(url_for(".report"))
