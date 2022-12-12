# Copyright (C) 2019  Keiron O'Shea <keo7@aber.ac.uk>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from flask import (
    redirect,
    abort,
    render_template,
    url_for,
    session,
    request,
    jsonify,
    Response,
    flash,
)
from flask_login import current_user, login_required

from .. import storage

from string import ascii_uppercase
import itertools
import re, csv
from datetime import datetime
import requests
from ...misc import get_internal_api_header
from uuid import uuid4
from ...decorators import check_if_admin

from ..forms import (
    NewSampleRackForm,
    EditSampleRackForm,
    SampleToEntityForm,
    SamplesToEntityForm,
    NewCryovialBoxFileUploadForm,
    CryoBoxFileUploadSelectForm,
    UpdateRackFileUploadForm,
)
from datetime import datetime

# def iter_all_strings():
#     for size in itertools.count(1):
#         for s in itertools.product(ascii_uppercase, repeat=size):
#             yield "".join(s)
#
#
# values = []
# for i in iter_all_strings():
#     values.append(i)
#     if i == "ZZZ":
#         break


@storage.route("/rack")
@login_required
def rack_index():
    response = requests.get(
        url_for("api.storage_rack_home", _external=True),
        headers=get_internal_api_header(),
    )

    if response.status_code == 200:
        return render_template(
            "storage/rack/index.html", racks=response.json()["content"]
        )

    return abort(response.status_code)


@storage.route("/rack/endpoint")
@login_required
def rack_endpoint():
    response = requests.get(
        url_for("api.storage_rack_home_tokenuser", _external=True),
        headers=get_internal_api_header(),
    )

    if response.status_code == 200:
        return response.json()
    return response.content


# @storage.route("/rack/endpoint_tokenuser")
# @login_required
# def rack_endpoint_tokenuser():
#     response = requests.get(
#         #url_for("api.storage_rack_info", _external=True),
#         url_for("api.storage_rack_home_toke", _external=True),
#         headers=get_internal_api_header(),
#     )
#
#     if response.status_code == 200:
#         return response.json()
#     return response.content


@storage.route("/rack/info")
@login_required
def rack_info():
    response = requests.get(
        url_for("api.storage_rack_info", _external=True),
        # url_for("api.storage_rack_home", _external=True),
        headers=get_internal_api_header(),
    )

    if response.status_code == 200:
        return response.json()
    return response.content


@storage.route("/rack/new", methods=["GET", "POST"])
@login_required
def add_rack():
    return render_template("storage/rack/new/option.html")


@storage.route("/rack/new/manual", methods=["GET", "POST"])
@login_required
def rack_manual_entry():
    form = NewSampleRackForm()
    if form.validate_on_submit():

        response = requests.post(
            url_for("api.storage_rack_new", _external=True),
            headers=get_internal_api_header(),
            json={
                "serial_number": form.serial.data,
                "num_rows": form.num_rows.data,
                "num_cols": form.num_cols.data,
                "colour": form.colours.data,
                "description": form.description.data,
            },
        )

        if response.status_code == 200:
            flash(
                "Sample Rack Added! Next: Assign the new rack to a cold storage shelf!!!"
            )
            # return redirect(url_for("storage.rack_index"))
            rack_id = response.json()["content"]["id"]
            return redirect(url_for("storage.edit_rack", id=rack_id))

    return render_template("storage/rack/new/manual/new.html", form=form)


def alpha2num(s):
    if s.isdigit():
        return s
    # Only the first letter will be used
    s = s.lower()
    num = 0
    for i in range(len(s)):
        num = num + (ord(s[-(i + 1)]) - 96) * (26 * i + 1)
    return num


def func_csvfile_to_json(csvfile, nrow=8, ncol=12) -> dict:

    data = {}
    try:
        reads = request.files[csvfile.name].read().decode().strip()
    except:
        try:
            reads = request.files[csvfile].read().decode().strip()
        except:
            return {
                "success": False,
                "message": "File reading error! Make sure the file is in csv format!",
            }

    if reads.startswith("'") and reads.endswith("'"):
        reads = reads[1:-1]

    csv_data = []

    expected_barcode = ["tube barcode", "barcode"]
    expected_uuid = ["identifier", "uuid"]
    expected_pos = ["tube position", "position", "pos"]
    resplit = re.compile(",")
    for linesep in ["\n", "\r\n", "\r"]:
        csvdata = reads.split(linesep)
        # print("csvdata", csvdata)
        # - check header
        if len(csvdata) < 2:
            continue

        header = [
            nm.lower().replace('"', "").replace("'", "")
            for nm in resplit.split(csvdata[0])
        ]

        res = list(set.intersection(*map(set, [header, expected_pos])))
        if len(res) == 0:
            continue

        res = list(
            set.intersection(*map(set, [header, (expected_barcode + expected_uuid)]))
        )
        if len(res) == 0:
            continue

        # if len(csvdata) != nrow * ncol + 1:
        #    continue
        csv_data = []
        for row in csvdata:
            row = row.split(",")
            row = [r.replace('"', "").replace("'", "").replace(",", "") for r in row]
            csv_data.append(row)

        if len(csv_data) >= 2:
            break

    if len(csv_data) < 2:
        return {
            "success": False,
            "message": "File reading error! Check if the file format is comma separated, with headers",
        }

    # print("nrows, Header", len(csv_data[0]), csv_data[0])
    print("header", header)
    indexes = {}

    for key in expected_pos:
        if key in header:
            indexes["position"] = header.index(key)

    if "position" not in indexes:
        return {
            "success": False,
            "message": "Missing column for tube position; "
            "should be one of the following in header (case insensitive): "
            "'Tube position', 'Position', 'Pos'",
        }

    for key in expected_barcode:
        if key in header:
            indexes["barcode"] = header.index(key)

    for key in expected_uuid:
        if key in header:
            indexes["uuid"] = header.index(key)

    if "barcode" not in indexes and "uuid" not in indexes:
        return {
            "success": False,
            "message": "Missing column for sample code; "
            "should be one of the following in header (case insensitive): "
            "'Tube barcode', 'Barcode', 'identifier', 'uuid'",
        }

    code_types = [key for key in indexes]

    indexes.update({"row": [], "column": []})

    print("codetype", code_types, indexes)

    positions = {
        # -- note: to ignore the second code in the same field separated by space.
        x[indexes["position"]]: {ct: x[indexes[ct]].split(" ")[0] for ct in code_types}
        for x in csv_data[1:]
    }
    print("positions", positions)

    data["positions"] = positions

    # Going to use plain old regex to do the splits
    regex = re.compile(r"(\d+|\s+)")

    for position in data["positions"].keys():
        splitted = regex.split(position)
        pos = []
        try:
            for s in splitted[0:2]:
                # print("s: ", s)
                if s.isdigit():
                    pos.append(int(s))
                else:
                    pos.append(ord(s.lower()) - 96)

            indexes["row"].append(pos[0])  # Letter e.g. A2: => Row 1
            indexes["column"].append(pos[1])  # Number A2 => Column 2
        except:
            return {"success": False, "message": "Error in reading positions"}

    if max(indexes["row"]) > nrow or min(indexes["row"]) < 1:
        return {"success": False, "message": "Position (row number) out of range!"}
    if max(indexes["column"]) > ncol or min(indexes["column"]) < 1:
        return {"success": False, "message": "Position (column number) out of range!"}

    data["num_rows"] = nrow  # max(indexes["row"])
    data["num_cols"] = ncol  # max(indexes["column"])
    data["code_types"] = code_types
    data["success"] = True
    return data


@storage.route("/rack/new/from_file", methods=["GET", "POST"])
@login_required
def rack_create_from_file():
    # ------
    # new the whole rack occupancy using csv file (often from the rack saner).
    # -----

    form = NewCryovialBoxFileUploadForm()

    if form.validate_on_submit():
        barcode_type = form.barcode_type.data
        err = None
        _samples = func_csvfile_to_json(
            form.file.data, form.num_rows.data, form.num_cols.data
        )

        if _samples["success"]:
            # print("barcode type", barcode_type, _samples["code_types"])
            if barcode_type not in _samples["code_types"]:
                err = (
                    "The provided sample code doesn't matched with the chosen type %s! "
                    % barcode_type
                )
        else:
            err = _samples["message"]

        if err:
            flash(err)
            return render_template(
                "storage/rack/new/from_file/step_one.html", form=form, session_data={}
            )

        samples = []
        for s in _samples["positions"].items():
            samples.append(
                {
                    "sample_code": s[1][barcode_type],
                    "row": alpha2num(s[0][0]),
                    "col": int(s[0][1 : len(s[0])]),
                }
            )

        rack_entry = {
            "serial_number": form.serial.data,
            "num_rows": form.num_rows.data,
            "num_cols": form.num_cols.data,
            "colour": form.colour.data,
            "description": form.description.data,
        }
        rack_data = {
            "rack_id": None,
            "barcode_type": form.barcode_type.data,
            "entry": form.entry.data,
            "entry_datetime": str(
                datetime.strptime(
                    "%s %s" % (form.entry_date.data, form.entry_time.data),
                    "%Y-%m-%d %H:%M:%S",
                )
            ),
            "samples": samples,
        }
        rack_data.update(rack_entry)

        rack_data["from_file"] = True
        sample_move_response = requests.post(
            url_for("api.storage_rack_refill_with_samples", _external=True),
            headers=get_internal_api_header(),
            json=rack_data,
        )

        if sample_move_response.status_code == 200:
            sampletostore = sample_move_response.json()["content"]
            sampletostore["new_rack"] = True
            sampletostore.update({"rack": rack_entry})

            return render_template(
                "storage/rack/view_sample_to_rack.html",
                id=id,
                sampletostore=sampletostore,
            )

        else:
            flash(sample_move_response.json()["message"])

    return render_template(
        "storage/rack/new/from_file/step_one.html", form=form, session_data={}
    )


# @storage.route("rack/new/automatic", methods=["GET", "POST"])
# @login_required
# def rack_automatic_entry():
#
#     form = NewCryovialBoxFileUploadForm()
#
#     if form.validate_on_submit():
#         _hash = str(uuid4())
#         replace with tempstore
#         session[_hash] = {
#             "serial_number": form.serial.data,
#             "num_rows": form.num_rows.data,
#             "num_cols": form.num_cols.data,
#             "barcode_type": form.barcode_type.data,
#             "colour": form.colour.data,
#             "description": form.description.data,
#             "entry": form.entry.data,
#             "entry_date": str(form.entry_date.data),
#             "entry_time": str(form.entry_time.data),
#             "json": func_csvfile_to_json(form.file.data, form.num_rows.data, form.num_cols.data)
#
#         }
#         err = None
#
#         barcode_type = form.barcode_type.data
#
#         _samples = func_csvfile_to_json(form.file.data, form.num_rows.data, form.num_cols.data)
#         if _samples["success"]:
#             print("barcode type", barcode_type, _samples["code_types"])
#             if barcode_type not in _samples["code_types"]:
#                 err = "The provided sample code doesn't matched with the chosen type %s! " %barcode_type
#         else:
#
#             err = _samples["message"]
#
#         if err is None:
#             rack_entry = {
#                 "serial_number": form.serial.data,
#                 "num_rows": form.num_rows.data,
#                 "num_cols": form.num_cols.data,
#                 "barcode_type": form.barcode_type.data,
#                 "colour": form.colour.data,
#                 "description": form.description.data,
#                 "entry": form.entry.data,
#                 "entry_date": str(form.entry_date.data),
#                 "entry_time": str(form.entry_time.data),
#                 "json": _samples
#             }
#
#             return render_template("storage/rack/new/from_file/step_two.html", form=form, session_data=rack_entry)
#
#     if err:
#         flash(err)
#     else:
#         flash("Errors in reading the file! ")
#     return render_template("storage/rack/new/from_file/step_one.html", form=form, session_data={})
#
#
# #- Not in use
# @storage.route("/rack/new/automatic/validation", methods=["GET", "POST"])
# @login_required
# def rack_automatic_entry_validation():
#     # def rack_automatic_entry_validation(_hash: str):
#     session_data = session[_hash]
#     if "json" not in values or "positions" not in values["json"]:
#        return {'messages': 'No sample and storage info for the rack!', 'success': False}
#
#     sample_data = {}
#
#     for position, identifier in values["json"]["positions"].items():
#         if identifier != "":
#             sample_response = requests.get(
#                 url_for("api.sample_query", _external=True),
#                 headers=get_internal_api_header(),
#                 json={session_data["barcode_type"]: identifier},
#             )
#
#             if sample_response.status_code == 200:
#                 sample = sample_response.json()["content"]
#                 sample_data[position] = sample
#
#     form = CryoBoxFileUploadSelectForm(sample_data, data=session_data["json"])
#
#     if form.validate_on_submit():
#
#         json = {
#             "serial_number": values["serial_number"],
#             "num_rows": values["json"]["num_rows"],
#             "num_cols": values["json"]["num_cols"],
#             "colour": values["colour"],
#             "description": values["description"],
#             "entry_datetime": str(
#                 datetime.strptime(
#                     "%s %s" % (values["entry_date"], values["entry_time"]),
#                     "%Y-%m-%d %H:%M:%S",
#                 )
#             ),
#             "entry": values["entry"],
#         }
#
#         _samples = []
#
#         for element in form:
#             if element.type == "BooleanField":
#                 if element.data:
#                     regex = re.compile(r"(\d+|\s+)")
#                     row, col, _ = regex.split(element.id)
#                     sample_code = element.render_kw["_sample"][0]["id"]
#                     _samples.append([row, col, sample_code])
#
#         samples_pos = []
#         for s in _samples:
#             samples_pos.append({
#                        "sample_code": s[2][barcode_type],
#                         "row": alpha2num(s[0]),
#                         "col": s[1],
#             }
#             ),
#
#         json["samples_pos"] = samples_pos
#         response = requests.post(
#             url_for("api.storage_rack_new_with_samples", _external=True),
#             headers=get_internal_api_header(),
#             json=json,
#         )
#
#         if response.status_code == 200:
#             response.json()["redirect"] = url_for("storage.view_rack", id=response.json()["content"]["id"])
#             # return redirect(
#             #     url_for("storage.view_rack", id=response.json()["content"]["id"])
#             # )
#
#         #flash("We have an issue!")
#         flash(response.json()["message"])
#         return response.json
#
#     return render_template(
#         "storage/rack/new/from_file/step_two.html",
#         session_data=session_data,
#         form=form,
#         hash=_hash,
#     )
#
#
# # @storage.route("/rack/new/automatic/validation/<_hash>", methods=["GET", "POST"])
# # @login_required
# def rack_automatic_entry_validation_div(_hash: str):
#     session_data = session[_hash]
#     sample_data = {}
#     # print("session_data: ", session_data)
#     for position, identifier in session_data["json"]["positions"].items():
#         sample = None
#         if "identifier" != "":
#             sample_response = requests.get(
#                 url_for("api.sample_query", _external=True),
#                 headers=get_internal_api_header(),
#                 json={session_data["barcode_type"]: identifier},
#             )
#
#             if sample_response.status_code == 200:
#                 sample = sample_response.json()["content"]
#                 sample_data[position] = sample
#
#     form = CryoBoxFileUploadSelectForm(sample_data, data=session_data["json"])
#
#     if form.validate_on_submit():
#         response = requests.post(
#             url_for("api.storage_rack_new", _external=True),
#             headers=get_internal_api_header(),
#             json={
#                 "serial_number": session_data["serial_number"],
#                 "num_rows": session_data["json"]["num_rows"],
#                 "num_cols": session_data["json"]["num_cols"],
#                 "colour": session_data["colour"],
#                 "description": session_data["description"],
#             },
#         )
#
#         if response.status_code == 200:
#
#             _samples = []
#
#             for element in form:
#                 if element.type == "BooleanField":
#                     if element.data:
#                         regex = re.compile(r"(\d+|\s+)")
#                         row, col, _ = regex.split(element.id)
#                         sample_id = element.render_kw["_sample"][0]["id"]
#                         _samples.append([sample_id, row, col])
#
#             responses = []
#
#             for s in _samples:
#
#                 sample_move_response = requests.post(
#                     url_for("api.storage_transfer_sample_to_rack", _external=True),
#                     headers=get_internal_api_header(),
#                     json={
#                         "sample_id": s[0],
#                         "rack_id": response.json()["content"]["id"],
#                         "row": s[1],  # s[2],
#                         "col": s[2],  # s[1],
#                         "entry_datetime": str(datetime.now()),
#                     },
#                 )
#
#                 responses.append([sample_move_response, s[0]])
#
#             return redirect(
#                 url_for("storage.view_rack", id=response.json()["content"]["id"])
#             )
#
#         flash("We have an issue!")
#
#     return render_template(
#         "storage/rack/new/from_file/step_two.html",
#         session_data=session_data,
#         form=form,
#         hash=_hash,
#     )


@storage.route("/rack/query/rack", methods=["GET", "POST"])
def check_rack_to_shelf():
    data = {}
    data["id"] = request.json["id"]
    response = requests.get(
        url_for("api.storage_rack_to_shelf_check", id=int(data["id"]), _external=True),
        headers=get_internal_api_header(),
    )

    data["warning"] = response.json()["content"]

    return jsonify(data)


@storage.route("/rack/query/sample", methods=["GET", "POST"])
def check_sample_to_rack():
    data = {}
    data["id"] = request.json["id"]
    response = requests.get(
        url_for(
            "api.storage_sample_to_entity_check", id=int(data["id"]), _external=True
        ),
        headers=get_internal_api_header(),
    )

    data["warning"] = response.json()["content"]

    return jsonify(data)


@storage.route("/rack/LIMBRACK-<id>")
@login_required
def view_rack(id):
    response = requests.get(
        url_for("api.storage_rack_view", id=id, _external=True),
        headers=get_internal_api_header(),
    )

    if response.status_code == 200:
        return render_template(
            "storage/rack/view.html", rack=response.json()["content"]
        )

    return abort(response.status_code)
    # return render_template("storage/rack/view.html", id=id)


@storage.route("/rack/LIMBRACK-<id>/endpoint")
@login_required
def view_rack_endpoint(id):
    def _assign_view(sample, rack_view):
        try:
            row, col = sample["row"], sample["col"]
            if sample["editor"] is None:
                sample["editor"] = sample["author"]

            rack_view["content"]["view"][row][col].update(sample)
            rack_view["content"]["view"][row][col].update(
                {
                    "empty": False,
                }
            )
            return 1, rack_view
        except Exception as e:
            pass
        return 0, rack_view

    view_response = requests.get(
        url_for("api.storage_rack_view", id=id, _external=True),
        headers=get_internal_api_header(),
    )

    if view_response.status_code == 200:
        rack_view = view_response.json()

        _rack = []
        for row in range(
            rack_view["content"]["num_rows"] + 1
        ):  # row, col: index in array
            _rack.append({})
            for col in range(rack_view["content"]["num_cols"] + 1):
                _rack[row][col] = {"empty": True}  # row+1, col+1: position in the rack

        # - Initialise rack_view['view'] to 2d array with empty cells
        rack_view["content"]["view"] = _rack

        count = 0
        # - fill in the cells with samples
        for sample in rack_view["content"]["entity_to_storage_instances"]:
            add, rack_view = _assign_view(sample, rack_view)
            count += add

        # rack_view["content"].pop("entity_to_storage_instances")
        total = rack_view["content"]["num_cols"] * rack_view["content"]["num_rows"]
        rack_view["content"]["counts"] = {"full": count, "empty": total - count}

        return rack_view
    return abort(view_response.status_code)


@storage.route("/rack/LIMBRACK-<id>/assign/<row>/<column>", methods=["GET", "POST"])
@login_required
def assign_rack_sample(id, row, column):
    # ------
    # Select and store a single sample to a rack position from the selected samples in user's Sample Cart.
    # -----
    view_response = requests.get(
        url_for("api.storage_rack_view", id=id, _external=True),
        headers=get_internal_api_header(),
    )

    if view_response.json()["content"]["is_locked"]:
        flash("The rack is locked!")
        return redirect(url_for("storage.view_rack", id=id))

    if view_response.json()["content"]["shelf"] is None:
        flash(
            "The rack has not been assigned to a shelf! Edit the rack location first!"
        )
        return redirect(url_for("storage.edit_rack", id=id))

    if view_response.status_code == 200:

        sample_response = requests.get(
            url_for("api.get_cart", _external=True),
            headers=get_internal_api_header(),
        )

        if sample_response.status_code == 200:
            samples = []
            for item in sample_response.json()["content"]:
                if item["selected"] and item["storage_type"] != "RUC":
                    samples.append(item["sample"])
            if len(samples) == 0:
                flash(
                    "Add samples to your sample cart and select from the cart first! "
                )
                return redirect(url_for("storage.view_rack", id=id))

            form = SampleToEntityForm(samples)

            if form.validate_on_submit():

                sample_move_response = requests.post(
                    url_for("api.storage_transfer_sample_to_rack", _external=True),
                    headers=get_internal_api_header(),
                    json={
                        "sample_id": form.samples.data,
                        "rack_id": id,
                        "row": row,
                        "col": column,
                        "entry_datetime": str(
                            datetime.strptime(
                                "%s %s" % (form.date.data, form.time.data),
                                "%Y-%m-%d %H:%M:%S",
                            )
                        ),
                        "entry": form.entered_by.data,
                    },
                )

                if sample_move_response.status_code == 200:
                    flash(sample_move_response.json()["message"])
                    return redirect(url_for("storage.view_rack", id=id))
                else:
                    flash(sample_move_response.json())

            return render_template(
                "storage/rack/sample_to_rack.html",
                rack=view_response.json()["content"],
                row=row,
                column=column,
                form=form,
            )

    abort(view_response.status_code)


@storage.route("/rack/LIMBRACK-<id>/assign_samples_in_cart", methods=["GET", "POST"])
@login_required
def assign_rack_samples(id):
    # ------
    # Select and store sample(s) to a rack from the selected samples in user's Sample Cart.
    # -----

    view_response = requests.get(
        url_for("api.storage_rack_view", id=id, _external=True),
        headers=get_internal_api_header(),
    )

    if view_response.json()["content"]["is_locked"]:
        flash("The rack is locked!")
        return redirect(url_for("storage.view_rack", id=id))

    if view_response.json()["content"]["shelf"] is None:
        flash(
            "The rack has not been assigned to a shelf! Edit the rack location first!"
        )
        return redirect(url_for("storage.edit_rack", id=id))

    if view_response.status_code == 200:

        sample_response = requests.get(
            url_for("api.get_cart", _external=True),
            headers=get_internal_api_header(),
        )

        if sample_response.status_code == 200:
            samples = []
            for item in sample_response.json()["content"]:
                if item["selected"] and item["storage_type"] != "RUC":
                    # samples.append({"id": item["sample"]["id"], "uuid": item["sample"]["uuid"]})
                    samples.append(item["sample"])

            if len(samples) == 0:
                flash("Add samples to your sample cart and select from the cart! ")
                return redirect(url_for("storage.view_rack", id=id))

            form = SamplesToEntityForm(samples)

            if form.validate_on_submit():
                sample_move_response = requests.post(
                    url_for("api.storage_rack_fill_with_samples", _external=True),
                    headers=get_internal_api_header(),
                    json={
                        "samples": [{"id": id1} for id1 in form.samples.data],
                        "rack_id": id,
                        "entry_datetime": str(
                            datetime.strptime(
                                "%s %s" % (form.date.data, form.time.data),
                                "%Y-%m-%d %H:%M:%S",
                            )
                        ),
                        "entry": form.entered_by.data,
                    },
                )

                if sample_move_response.status_code == 200:
                    sampletostore = sample_move_response.json()["content"]
                    for sample in sampletostore["samples"]:
                        for item in sample_response.json()["content"]:
                            if item["sample"]["id"] == sample["id"]:
                                sample.update(item["sample"])

                    return render_template(
                        "storage/rack/view_sample_to_rack.html",
                        id=id,
                        sampletostore=sampletostore,
                    )

                else:
                    flash(sample_move_response.json())
                    return redirect(url_for("storage.view_rack", id=id))

            return render_template(
                "storage/rack/sample_to_rack.html",
                rack=view_response.json()["content"],
                form=form,
            )

    return abort(view_response.status_code)


@storage.route(
    "/rack/LIMBRACK-<id>/auto_assign_sample_to_rack", methods=["GET", "POST"]
)
@login_required
def auto_assign_sample_to_rack(id):
    return render_template("storage/rack/view_sample_to_rack.html", id=id)


@storage.route("/rack/fill_with_samples", methods=["GET", "POST"])
@login_required
def storage_rack_fill_with_samples():
    if request.method == "POST":
        values = request.json
    else:
        return {"messages": "Sample and storage info needed!", "success": False}

    response = requests.post(
        url_for("api.storage_rack_fill_with_samples", _external=True),
        headers=get_internal_api_header(),
        json=values,
    )
    return response.json()


@storage.route("/rack/LIMBRACK-<id>/edit_samples_in_rack", methods=["GET", "POST"])
@login_required
def edit_rack_samples_pos(id):
    view_response = requests.get(
        url_for("api.storage_rack_view", id=id, _external=True),
        headers=get_internal_api_header(),
    )

    if view_response.json()["content"]["is_locked"]:
        flash("The rack is locked!")
        return redirect(url_for("storage.view_rack", id=id))

    if view_response.json()["content"]["shelf"] is None:
        flash(
            "The rack has not been assigned to a shelf! Edit the rack location first!"
        )
        return redirect(url_for("storage.edit_rack", id=id))

    sampletostore = view_response.json()["content"]
    id = int(sampletostore.pop("id"))
    sampletostore = {
        "rack_id": id,
        "samples": [],
        "from_file": False,
        "update_only": True,
    }

    return render_template(
        "storage/rack/view_sample_to_rack.html", id=id, sampletostore=sampletostore
    )


@storage.route("/rack/edit_samples_pos", methods=["GET", "POST"])
@login_required
def storage_rack_edit_samples_pos():
    if request.method == "POST":
        values = request.json
    else:
        return {"messages": "Sample and storage info needed!", "success": False}

    response = requests.post(
        url_for("api.storage_rack_edit_samples_pos", _external=True),
        headers=get_internal_api_header(),
        json=values,
    )
    return response.json()


@storage.route("/rack/LIMBRACK-<id>/assign_samples_in_file", methods=["GET", "POST"])
@login_required
def update_rack_samples(id):
    # ------
    # Update the whole rack occupancy using csv file (often from the rack saner).
    # -----
    view_response = requests.get(
        url_for("api.storage_rack_view", id=id, _external=True),
        headers=get_internal_api_header(),
    )

    if view_response.json()["content"]["is_locked"]:
        flash("The rack is locked!")
        return redirect(url_for("storage.view_rack", id=id))

    if view_response.json()["content"]["shelf"] is None:
        flash(
            "The rack has not been assigned to a shelf! Edit the rack location first!"
        )
        return redirect(url_for("storage.edit_rack", id=id))

    if view_response.status_code == 200:
        num_rows = view_response.json()["content"]["num_rows"]
        num_cols = view_response.json()["content"]["num_cols"]

        form = UpdateRackFileUploadForm()

        if form.validate_on_submit():
            barcode_type = form.barcode_type.data

            err = None

            _samples = func_csvfile_to_json(form.file.data, num_rows, num_cols)
            if _samples["success"]:
                print("barcode type", barcode_type, _samples["code_types"])
                if barcode_type not in _samples["code_types"]:
                    err = (
                        "The provided sample code doesn't matched with the chosen type %s! "
                        % barcode_type
                    )
            else:
                # err = "Errors in reading the file! "
                err = _samples["message"]

            if err:
                flash(err)
                return redirect(url_for("storage.view_rack", id=id))

            samples = []
            for s in _samples["positions"].items():
                samples.append(
                    {
                        "sample_code": s[1][barcode_type],
                        "row": alpha2num(s[0][0]),
                        "col": int(s[0][1 : len(s[0])]),
                    }
                )

            rack_data = {
                # "samples": [{"id": id1} for id1 in form.samples.data],
                "rack_id": id,
                "entry_datetime": str(
                    datetime.strptime(
                        "%s %s" % (form.entry_date.data, form.entry_time.data),
                        "%Y-%m-%d %H:%M:%S",
                    )
                ),
                "entry": form.entry.data,
                "barcode_type": form.barcode_type.data,
                "samples": samples,
            }

            sample_move_response = requests.post(
                url_for("api.storage_rack_refill_with_samples", _external=True),
                headers=get_internal_api_header(),
                json=rack_data,
            )

            if sample_move_response.status_code == 200:
                sampletostore = sample_move_response.json()["content"]

                return render_template(
                    "storage/rack/view_sample_to_rack.html",
                    id=id,
                    sampletostore=sampletostore,
                )

            else:
                flash(sample_move_response.json())
                return redirect(url_for("storage.view_rack", id=id))

        return render_template(
            "storage/rack/sample_to_rack_from_file.html",
            rack=view_response.json()["content"],
            form=form,
        )
    return abort(view_response.status_code)


@storage.route("/rack/new_with_samples", methods=["GET", "POST"])
@login_required
def storage_rack_create_with_samples():
    if request.method == "POST":
        values = request.json
    else:
        return {"messages": "Sample and storage info needed!", "success": False}

    response = requests.post(
        url_for("api.storage_rack_new_with_samples", _external=True),
        headers=get_internal_api_header(),
        json=values,
    )
    return response.json()


@storage.route("/rack/refill_with_samples", methods=["GET", "POST"])
@login_required
def storage_rack_refill_with_samples():
    if request.method == "POST":
        values = request.json
    else:
        return {"messages": "Sample and storage info needed!", "success": False}

    response = requests.post(
        url_for("api.storage_rack_refill_with_samples", _external=True),
        headers=get_internal_api_header(),
        json=values,
    )
    return response.json()


@storage.route("rack/LIMBRACK-<id>/to_cart", methods=["GET", "POST"])
@login_required
def add_rack_to_cart(id):
    view_response = requests.get(
        url_for("api.storage_rack_view", id=id, _external=True),
        headers=get_internal_api_header(),
    )

    if view_response.status_code == 200:
        to_cart_response = requests.post(
            url_for("api.add_rack_to_cart", id=id, _external=True),
            headers=get_internal_api_header(),
        )
        redirect(url_for("storage.view_rack", id=id))
        return to_cart_response.content
    return abort(view_response.status_code)


@storage.route("rack/LIMBRACK-<id>/edit", methods=["GET", "POST"])
@login_required
def edit_rack(id):
    response = requests.get(
        url_for("api.storage_rack_view", id=id, _external=True),
        headers=get_internal_api_header(),
    )
    if response.json()["content"]["is_locked"]:
        flash("The rack is locked!")
        return abort(401)

    if response.status_code == 200:
        response = requests.get(
            url_for("api.storage_rack_location", id=id, _external=True),
            # url_for("api.storage_rack_view", id=id, _external=True),
            headers=get_internal_api_header(),
        )

        sites_response = requests.get(
            url_for("api.site_home_tokenuser", _external=True),
            headers=get_internal_api_header(),
        )

        if sites_response.status_code == 200:
            sites = sites_response.json()["content"]["choices"]
            user_site_id = sites_response.json()["content"]["user_site_id"]

        # For SampleRack with location info.
        rack = response.json()["content"]
        # print("Rack: ", rack)
        shelves = []
        shelf_dict = {}
        shelf_required = True
        response1 = requests.get(
            url_for("api.storage_shelf_overview", _external=True),
            # url_for("api.storage_onsite_shelves", id=id, _external=True),
            headers=get_internal_api_header(),
        )

        if response1.status_code == 200:

            for site in sites:
                shelf_dict[site[0]] = []

            for shelf in response1.json()["content"]["shelf_info"]:
                shelf_dict[int(shelf["site_id"])].append(
                    [int(shelf["shelf_id"]), shelf["name"]]
                )
                shelves.append([int(shelf["shelf_id"]), shelf["name"]])

            # shelf_required = len(shelves) > 0

        form = EditSampleRackForm(
            sites=sites,
            shelves=shelves,
            data={
                "serial": rack["serial_number"],
                "description": rack["description"],
                "storage_id": rack["storage_id"],
                "shelf_id": rack["shelf_id"],
            },
        )

        delattr(form, "num_cols")
        delattr(form, "num_rows")
        delattr(form, "colours")
        # if not shelf_required:
        #    delattr(form, "shelf_id")

        if form.validate_on_submit():
            shelf_id = form.shelf_id.data
            if shelf_id == 0:
                shelf_id = None

            form_information = {
                "serial_number": form.serial.data,
                "description": form.description.data,
                "storage_id": form.storage_id.data,
                "shelf_id": shelf_id,
            }

            edit_response = requests.put(
                url_for("api.storage_rack_edit", id=id, _external=True),
                headers=get_internal_api_header(),
                json=form_information,
            )

            if edit_response.status_code == 200:
                flash("Rack Successfully Edited")
                return redirect(url_for("storage.view_rack", id=id))

            else:
                flash("We have a problem: %s" % (edit_response.json()["message"]))

        return render_template(
            "storage/rack/edit.html",
            form=form,
            rack=response.json()["content"],
            shelves=shelf_dict,
        )

    abort(response.status_code)


@storage.route("/rack/LIMBRACK-<id>/delete", methods=["GET", "POST"])
@login_required
def delete_rack(id):
    response = requests.get(
        url_for("api.storage_rack_view", id=id, _external=True),
        headers=get_internal_api_header(),
    )

    if response.json()["content"]["is_locked"]:
        return abort(401)

    if response.status_code == 200:
        edit_response = requests.post(
            url_for("api.storage_rack_delete", id=id, _external=True),
            headers=get_internal_api_header(),
        )
        if edit_response.status_code == 200:
            flash("Rack Successfully Deleted")
            if edit_response.json()["content"] is None:
                return redirect(url_for("storage.rack_index"))
            return redirect(
                url_for(
                    "storage.view_shelf",
                    id=edit_response.json()["content"],
                    _external=True,
                )
            )

        else:
            flash("We have a problem. %s " % edit_response.json()["message"])

        return redirect(url_for("storage.view_rack", id=id, _external=True))

    abort(response.status_code)


@storage.route("/rack/LIMBRACK-<id>/lock", methods=["GET", "POST"])
@login_required
@check_if_admin
def lock_rack(id):

    response = requests.get(
        url_for("api.storage_rack_view", id=id, _external=True),
        headers=get_internal_api_header(),
    )
    if response.status_code == 200:
        edit_response = requests.post(
            url_for("api.storage_rack_lock", id=id, _external=True),
            headers=get_internal_api_header(),
        )

        if edit_response.status_code == 200:
            if edit_response.json()["content"]:
                flash("Rack Successfully Locked")
            else:
                flash("Rack Successfully Unlocked")
        else:
            flash("We have a problem: %s" % (edit_response.status_code))

        return redirect(url_for("storage.view_rack", id=id))

    return abort(response.status_code)
