from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from ..database import dao
from ..database.dao.exceptions import RowDoesNotExist
from ..helpers.calculations import html_date

reminder = Blueprint("reminder", __name__)


@reminder.route("/view", methods=["GET", "POST"])
@login_required
def view():
    loaded_reminders = ()
    r_type_id = None
    if request.method == "POST":
        try:
            r_type_id = request.form.get("reminder-type-id", None, int)
            show_removed = request.form.get("show-removed", False, bool)
            if r_type_id:
                loaded_reminders = dao.reminder.get_reminders(
                    reminder_type_id=r_type_id,
                    removed=show_removed)
            else:
                loaded_reminders = dao.reminder.get_reminders(
                    removed=show_removed)
        except KeyError:
            flash("Missing required form data", "error")
    return render_template(
        "reminder/view.html",
        reminders=loaded_reminders, types=dao.reminder.get_reminder_types(), r_type_id=r_type_id)


@reminder.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        try:
            content = request.form["reminder-content"]
            user_for_id = request.form.get("user-for", None, int)
            r_type = request.form["reminder-type"]
            is_priority = request.form.get("priority", False, bool)
            datedue = request.form.get("datedue", None, html_date)
            tasks = request.form.getlist("atask")

            added_reminder = dao.reminder.new_reminder(
                content, r_type, is_priority,
                datedue, user_for_id)
            if tasks:
                dao.reminder.new_reminder_task(added_reminder.id_, *tasks)
            flash("added entry!")
        except KeyError:
            flash("Missing required form data", "error")
    return render_template(
        "reminder/new.html", users=dao.user.get_users(),
        reminder_types=dao.reminder.get_reminder_types())


@reminder.route("/edit/<int:reminder_id>", methods=["GET", "POST"])
@login_required
def edit(reminder_id):
    if request.method == "POST":
        removed = bool(request.form.get("removed", False))
        try:
            if removed:
                dao.reminder.remove_reminder(reminder_id)
                flash("Entry marked for removal")
            else:
                dao.reminder.remove_reminder(reminder_id, False)
                flash("Entry no longer marked for removal")
        except RowDoesNotExist:
            flash("reminder with that id does not exist!", "warning")
        return redirect(url_for(".view"))
    loaded_reminder = dao.reminder.get_reminders(
        only_first=True, id_=reminder_id)
    loaded_tasks = dao.reminder.get_reminder_tasks(
        reminder_id=reminder_id, removed=False)
    return render_template(
        "/reminder/edit.html",
        reminder=loaded_reminder, tasks=loaded_tasks)


@reminder.route("/edit/<int:reminder_id>/new-task", methods=["GET", "POST"])
@login_required
def new_task(reminder_id):
    if request.method == "POST":
        tasks = request.form.getlist("atask")
        if tasks:
            dao.reminder.new_reminder_task(reminder_id, *tasks)
        return redirect(url_for(".edit", reminder_id=reminder_id))
    loaded_reminder = dao.reminder.get_reminders(
        only_first=True, removed=False)
    return render_template("reminder/new_tasks.html", reminder=loaded_reminder)


@reminder.route("/remove/<int:item_id>")
@login_required
def remove_reminder(item_id: int):
    dao.reminder.remove_reminder(item_id, True)
    flash("removed reminder")
    return redirect(url_for(".view"))


@reminder.route("/restore/<int:item_id>")
@login_required
def restore_reminder(item_id: int):
    dao.reminder.remove_reminder(item_id, False)
    flash("restored reminder")
    return redirect(url_for(".view"))
