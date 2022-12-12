from flask import (Blueprint, abort, current_app, flash, jsonify, redirect,
                   render_template, request, send_file, url_for)
from flask_login import login_required

from ..database.dao import photo_manager as dao_pm
from ..database.dao.exceptions import RowDoesNotExist
from ..database.dao.user import get_users
from ..helpers.calculations import html_date
from ..helpers.paths import get_image_folder, is_allowed_img_file
from ..helpers.photos import compress_jpg_thumbnail

pm = Blueprint("pm", __name__)


@pm.route("/report-subloc", methods=["GET"])
@login_required
def get_subloc():
    main_loc = request.args.get("mainloc", default="", type=str)
    sublocations = dao_pm.get_subloc(main_loc)
    if len(sublocations) > 0:
        return jsonify(main_loc=main_loc, sublocs=[subloc.serialize() for subloc in sublocations])
    return jsonify(sublocs=[])


@pm.route("/thumbnails/<int:event_id>.jpg")
@login_required
def thumbnail(event_id):
    filename = dao_pm.get_thumbnail_fn(event_id)
    if filename:
        full_path = get_image_folder("PHOTO_MANAGER") / filename
        return send_file(full_path)
    return abort(404)


@pm.route("/", methods=["GET", "POST"])
@login_required
def view():
    loaded_entries = ()
    filter_by = "(Please use display button to filter)"
    if request.method == "POST":
        mainloc = request.form.get("main-location")
        subloc = request.form.get("sub-location")
        sort_by_date = bool(request.form.get("sort-by-date", False, int))
        if not mainloc:
            filter_by = "Showing All"
            loaded_entries = dao_pm.get_event(sort_dated=sort_by_date)
        elif mainloc and not subloc:
            filter_by = mainloc
            loaded_entries = dao_pm.get_event(mainloc, sort_dated=sort_by_date)
        else:
            filter_by = mainloc
            if subloc:
                filter_by = filter_by + " > " + subloc
            try:
                loaded_entries = dao_pm.get_event(
                    mainloc, subloc, sort_by_date)
            except RowDoesNotExist:
                flash(f"sub location '{subloc}' does not exist", "error")
    main_locations = dao_pm.get_mainloc()
    return render_template(
        "/photo_manager/view.html", main_locations=main_locations,
        loaded_entries=loaded_entries, filter_by=filter_by)


@pm.route("/new", methods=["GET", "POST"])
@login_required
def new():
    if request.method == "POST":
        try:
            mainloc = request.form["mainloc"]
            subloc = request.form["subloc"]
            datetaken = request.form.get("datetaken", type=html_date)
            if not datetaken:
                raise KeyError("no datetaken keyword exists")
            notes = request.form["notes"]
            users = request.form.getlist("user", type=str)
            picture = request.files.get("pic", None)
            if users:
                if picture:
                    if is_allowed_img_file(picture.filename):
                        bytes_picture = compress_jpg_thumbnail(
                            picture,
                            current_app.config["MAX_IMAGE_SIZE"],
                            current_app.config["JPEG_QUALITY"])
                    else:
                        flash("image is not in allowed format", "error")
                        return redirect(url_for(".new"))
                else:
                    bytes_picture = None
                dao_pm.new_event(mainloc, subloc, datetaken,
                                 notes, users, bytes_picture)
                flash("added entry")
            else:
                flash("not added as no users were selected", "warning")
        except KeyError as err:
            flash(f"Missing required fields!, {err.args}", "error")
    main_locations = dao_pm.get_mainloc()
    users = get_users()
    return render_template("photo_manager/new.html", main_locations=main_locations, users=users)


@pm.route("/edit-sub-location", methods=["GET", "POST"])
@login_required
def edit_sub_location():
    if request.method == "POST":
        try:
            main_loc_name = request.form["mainloc-name"]
            sub_loc_name = request.form["subloc-name"]
            lat = request.form["subloc-lat"]
            lng = request.form["subloc-lng"]
            removed = request.form.get("removed", False, bool)
        except KeyError:
            flash("Missing required fields!", "error")

        dao_pm.new_subloc(sub_loc_name, lat, lng, main_loc_name, removed)
        flash("added new location")

    main_locations = dao_pm.get_mainloc()
    return render_template("photo_manager/edit-sub-location.html", main_locations=main_locations)
