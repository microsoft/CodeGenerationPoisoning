from flask import render_template, url_for
from app.members import blueprint
from flask_socketio import emit
from app import socketio
from flask_login import current_user, login_required
import app.users as users


@blueprint.route("/members")
@login_required
def members():
    return render_template("members.html")


@socketio.on("request_members")
def send_member_table():
    stripped_members = users.read_quota_list()

    emit("member_list", {"data": stripped_members})
