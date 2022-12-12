from flask import Blueprint, flash, jsonify, render_template, request
from flask_login import current_user, login_required

from ..database import dao
from ..database.dao.exceptions import RowDoesNotExist
from ..helpers.api import api_auth, api_date_checks
from ..helpers.server_messaging.types import (DBUpdateTypes, MessageTypes,
                                              Payload, ServerMessage)
from ..sockets import message_handler

messages = Blueprint("messages", __name__)


@messages.route("/")
@login_required
def view():
    loaded_messages = dao.user.get_messages()
    return render_template("messages/view.html", messages=loaded_messages)


@messages.route("/asjson")
@api_auth
@api_date_checks
def view_json():
    loaded_messages = dao.user.get_messages(
        last_updated=request.args.get("last-update"))
    return jsonify(loaded_data=[message.serialize() for message in loaded_messages])


@messages.route("/new", methods=["POST", "GET"])
@login_required
def new_message():
    if request.method == "POST":
        message = request.form.get("message")
        if message:
            added_message = dao.user.new_message(current_user.id_, message)
            if added_message:
                live_update_payload = Payload.create_dbupdate(
                    DBUpdateTypes.ADD,
                    "messages",
                    added_message.id_)
                live_update_mess = ServerMessage(
                    MessageTypes.DB_UPDATE,
                    live_update_payload)
                message_handler.send_message(
                    live_update_mess, app_name="messages")
                flash("Message saved!")
        else:
            flash("required form details missing", "error")
    return render_template("messages/new_message.html")


@messages.route("/remove/<mess_id>", methods=["DELETE"])
@api_auth
def remove_message(mess_id):
    try:
        dao.user.remove_message(mess_id)
        live_update_payload = Payload.create_dbupdate(
            DBUpdateTypes.DELETE,
            "messages",
            mess_id)
        live_update_mess = ServerMessage(
            MessageTypes.DB_UPDATE,
            live_update_payload)
        message_handler.send_message(live_update_mess, app_name="messages")
    except RowDoesNotExist:
        pass
    # return 204 status code as no further information is supplied
    return "", 204
