from flask import render_template
from flask_socketio import emit
from flask_login import current_user, login_required

from app import socketio
from app import db
from app.profile import blueprint
import app.users as users
from app.errors.flashed import FlashedError, flashed_errors_forwarded


@blueprint.route("/profile")
@login_required
def profile():
    return render_template("profile.html")


@socketio.on("set_active")
def set_active(active):
    users.set_active(current_user, active)
    send_user_status()


@socketio.on("change_password")
@flashed_errors_forwarded
def change_password(data):
    if data["new_password"] != data["new_password_repeat"]:
        raise PasswordRepeatError
    if len(data["new_password"]) < 6:
        raise PasswordShortError
    if not current_user.check_password(data["old_password"]):
        raise InvalidPasswordError
    current_user.set_password(data["new_password"])
    db.session.commit()
    emit("password_success")


@socketio.on("request_status")
def send_user_status():
    user_schema = users.UserSchema()
    data = user_schema.dump(current_user)
    del data["password_hash"]
    emit("current_user", {"data": data})


class InvalidPasswordError(FlashedError):
    user_description = "You current password was invalid."


class PasswordRepeatError(FlashedError):
    user_description = "Your password repeat did not match."


class PasswordShortError(FlashedError):
    user_description = "Your new password is too short."
