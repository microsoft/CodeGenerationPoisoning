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

from .. import sample

from flask import render_template, redirect, session, url_for, request, abort, flash
from flask_login import login_required, current_user
import requests


from ...database import db
from ..forms import SampleAliquotingForm, SampleDerivationForm
from ...misc import get_internal_api_header


@sample.route("<uuid>/aliquot", methods=["GET", "POST"])
@login_required
def aliquot(uuid: str):
    # An aliquot creates a specimen from the same type as the parent.

    protocols_response = requests.get(
        url_for("api.protocol_query_tokenuser", default_type="ALD", _external=True),
        headers=get_internal_api_header(),
        json={"is_locked": False, "type": ["ALD"]},
    )

    if protocols_response.status_code == 200:
        aliquot_protocols = protocols_response.json()["content"]["choices"]

    else:
        flash("No sample aliquot/derivation protocol!")
        return render_template("sample/view.html", uuid=uuid)

    form = SampleAliquotingForm(aliquot_protocols)

    return render_template(
        "sample/aliquot/create.html",
        form=form,
        aliquot_proc_count=len(aliquot_protocols),
    )


@sample.route("query", methods=["POST"])
@login_required
def query():
    values = request.get_json()

    if not values:
        return {"Err": "No values"}

    query_response = requests.post(
        url_for("api.sample_query", _external=True),
        headers=get_internal_api_header(),
        json=values,
    )

    if query_response.status_code == 200:
        return query_response.json()
    else:
        return {"Err": query_response.status_code}


@sample.route("<uuid>/aliquot/endpoint", methods=["POST"])
@login_required
def aliquot_endpoint(uuid: str):
    values = request.get_json()

    if not values:

        return {"Err": "No values provided."}

    aliquot_response = requests.post(
        url_for("api.sample_new_aliquot", uuid=uuid, _external=True),
        headers=get_internal_api_header(),
        json=values,
    )

    if aliquot_response.status_code == 200:
        return aliquot_response.json(), aliquot_response.status_code

    return aliquot_response.content, aliquot_response.status_code


@sample.route("<uuid>/derive", methods=["GET", "POST"])
@login_required
def derive(uuid: str):
    # This function will record both processing and derivation protocol events
    # A derivative creates a different specimen type from the parent.

    protocols_response = requests.get(
        url_for("api.protocol_query_tokenuser", default_type="SAP", _external=True),
        headers=get_internal_api_header(),
        json={"is_locked": False, "type": ["SAP"]},
    )
    if protocols_response.status_code == 200:
        processing_protocols = protocols_response.json()["content"]["choices"]
        processing_protocols = processing_protocols + [[0, "None"]]
    else:
        processing_protocols = [0, "None"]

    protocols_response = requests.get(
        url_for("api.protocol_query_tokenuser", default_type="ALD", _external=True),
        headers=get_internal_api_header(),
        json={"is_locked": False, "type": ["ALD"]},
    )

    if protocols_response.status_code == 200:
        aliquot_protocols = protocols_response.json()["content"]["choices"]

    else:
        flash("No sample aliquot/derivation protocol!")
        return render_template("sample/view.html", uuid=uuid)

    form = SampleDerivationForm(processing_protocols, aliquot_protocols)

    return render_template(
        "sample/aliquot/derive.html",
        form=form,
        derivie_proc_count=len(aliquot_protocols),
    )


@sample.route("<uuid>/derive/endpoint", methods=["POST"])
@login_required
def derive_endpoint(uuid: str):
    values = request.get_json()

    if not values:

        return {"Err": "No values provided."}

    derive_response = requests.post(
        url_for("api.sample_new_derivative", uuid=uuid, _external=True),
        headers=get_internal_api_header(),
        json=values,
    )

    if derive_response.status_code == 200:
        return derive_response.json(), derive_response.status_code

    return derive_response.content, derive_response.status_code
