from uuid import UUID

from flask import (Blueprint, Response, current_app, jsonify, render_template,
                   request, stream_with_context, url_for)
from flask_login import current_user, login_required
from werkzeug.routing import BuildError

from ..database import dao
from ..helpers.checkers import is_admin
from ..helpers.types import Widget
from ..helpers.widgets import generate_widget_container, generate_widget_failed

home = Blueprint("home", __name__)


@home.context_processor
def context_get_messages():
    return dict(get_messages=dao.user.get_messages)


@home.route("/dashboard")
@login_required
def dashboard():
    return render_template("/home/dashboard.html")


@home.route("/cc")
@login_required
def command_center():
    return render_template("home/command_center.html", admin=is_admin(current_user.username))


@home.route("/view-plugins")
@login_required
def view_plugins():
    return render_template("home/plugins.html")


@home.route("/dashboard/widgets/get-all")
@login_required
def get_dashboard_widgets():
    def stream_response():
        for widget_row in dao.dashboard.get_dashboard_widget_order(current_user.id_):
            try:
                widget_info: Widget = current_app.config["WIDGETS"][widget_row.widget_uuid]
                widget_html = widget_info.generation_func(
                    widget_row.id_,
                    widget_row.widget_settings)
                yield generate_widget_container(widget_row.id_, widget_html)
            except (KeyError, BuildError):
                current_app.logger.exception("widget failed to load")
                dao.dashboard.remove_widget(widget_row.id_)
                yield generate_widget_failed(widget_row.id_)
    return Response(stream_with_context(stream_response()))


@home.route("/dashboard/widgets/get-names")
@login_required
def get_widget_names():
    return jsonify([{"name": value.name, "uuid": value.uuid}
                    for value in current_app.config["WIDGETS"].values()])


@home.route("/dashboard/widgets/get-setting-url/<widget_id>")
@login_required
def get_widget_settings_url(widget_id):
    try:
        widget_id = int(widget_id)
        widget = dao.dashboard.get_widget(current_user.id_, widget_id)
        if widget:
            endpoint = current_app.config["WIDGETS"][widget.widget_uuid].settings_endpoint
            if endpoint:
                return jsonify(settings_url=url_for(endpoint, widget_id=widget_id))
        return jsonify(settings_url=None)
    except (TypeError, ValueError):
        return jsonify(error="incorrect datatype sent"), 400


@home.route("/dashboard/widgets/add", methods=["POST"])
@login_required
def add_widget():
    try:
        json_form = request.json
        id_to_replace = json_form["id-to-replace"]
        if id_to_replace is not None:
            id_to_replace = int(id_to_replace)
        # convert 'uuid' str into UUID
        widget_uuid = UUID(json_form["widget-uuid"], version=4)
        # add widget to db
        widget_row = dao.dashboard.add_widget(
            current_user.id_, widget_uuid, id_to_replace)
        # generate for the user and return
        widget_info: Widget = current_app.config["WIDGETS"][widget_uuid]
        widget_html = widget_info.generation_func(
            widget_row.id_,
            widget_row.widget_settings)
        return generate_widget_container(widget_row.id_, widget_html)
    except KeyError:
        return jsonify(error="missing required values"), 400
    except (TypeError, ValueError):
        return jsonify(error="incorrect datatype sent"), 400


@home.route("/dashboard/widgets/remove", methods=["DELETE"])
@login_required
def delete_widget():
    try:
        widget_id = int(request.json["id"])
        dao.dashboard.remove_widget(widget_id)
        return ""
    except KeyError:
        return jsonify(error="missing required values"), 400
    except ValueError:
        return jsonify(error="incorrect datatype sent"), 400


@home.route("/dashboard/widgets/move", methods=["PUT"])
@login_required
def move_widget():
    try:
        the_json = request.json
        widget_id = int(the_json["id"])
        id_to_replace = int(the_json["id-to-replace"])
        dao.dashboard.move_widget(widget_id, id_to_replace, current_user.id_)
        return ""
    except KeyError:
        return jsonify(error="missing required values"), 400
    except ValueError:
        return jsonify(error="incorrect datatype sent"), 400
