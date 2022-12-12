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
import requests
from flask import json, render_template, url_for, flash, redirect, abort, request
from flask_login import login_required

import requests
from ...misc import get_internal_api_header

from ..forms import (
    SampleToDocumentAssociatationForm,
    SampleReviewForm,
    ProtocolEventForm,
    EditBasicForm,
)

from ..enums import BiohazardLevel, Colour

from datetime import datetime


@sample.route("<uuid>", methods=["GET"])
@login_required
def view(uuid: str):
    return render_template("sample/view.html", uuid=uuid)


@sample.route("<uuid>/cart/add", methods=["POST", "PUT"])
@login_required
def add_sample_to_cart(uuid):
    sample_response = requests.get(
        url_for("api.sample_view_sample", uuid=uuid, _external=True),
        headers=get_internal_api_header(),
    )

    if sample_response.status_code == 200:
        cart_response = requests.post(
            url_for("api.add_sample_to_cart", uuid=uuid, _external=True),
            headers=get_internal_api_header(),
        )

        return cart_response.content

    return sample_response.content


@sample.route("to_cart", methods=["POST"])
@sample.route("to_cart/LIMBUSR-<user_id>", methods=["POST"])
@login_required
def add_samples_to_cart(user_id=None):
    samples = []
    if request.method == "POST":
        values = request.json
        samples = values.pop("samples", [])

    if len(samples) == 0:
        return {"success": False, "messages": "No sample selected!"}

    to_cart_response = requests.post(
        url_for("api.add_samples_to_cart", user_id=user_id, _external=True),
        headers=get_internal_api_header(),
        json={"samples": [{"id": sample["id"]} for sample in samples]},
    )

    if to_cart_response.status_code == 200:
        return to_cart_response.json()

    return to_cart_response.json()


@sample.route("/cart/LIMBUSR-<user_id>/reassign", methods=["GET", "POST"])
@login_required
def reassign_sample_cart(user_id):
    if request.method == "POST":
        values = request.json
    else:
        return {"message": "Use id info needed!", "success": False}

    to_cart_response = requests.post(
        url_for("api.sample_reassign_cart", user_id=user_id, _external=True),
        headers=get_internal_api_header(),
        json={"new_user_id": values["new_user_id"]},
        # json={"samples": values["samples"], "new_user_id":  values["new_user_id"]},
    )

    return to_cart_response.json()


#
# @sample.route("to_cart", methods=["POST"])
# @login_required
# def add_samples_to_cart():
#     samples = []
#     if request.method == "POST":
#         values = request.json
#         samples = values.pop("samples", [])
#
#     if len(samples) == 0:
#         return {"success": False, "messages": "No sample selected!"}
#
#     to_cart_response = requests.post(
#         url_for("api.add_samples_to_cart", _external=True),
#         headers=get_internal_api_header(),
#         json={"samples": [{"id": sample["id"]} for sample in samples]},
#     )
#
#     if to_cart_response.status_code == 200:
#         return to_cart_response.json()
#
#     return to_cart_response.json()


@sample.route("samples_shipment_to_cart", methods=["POST"])
@login_required
def add_samples_shipment_to_cart():
    samples = []
    if request.method == "POST":
        values = request.json
    #     shipment = values.pop('shipment', [])
    #
    # if len(samples) == 0:
    #    return {'success': False, 'messages': 'No sample selected!'}

    to_cart_response = requests.post(
        url_for("api.add_samples_in_shipment_to_cart", _external=True),
        headers=get_internal_api_header(),
        json=values,
    )

    if to_cart_response.status_code == 200:
        return to_cart_response.json()

    return to_cart_response.json()


@sample.route("<uuid>/cart/remove", methods=["DELETE"])
@sample.route("/cart/LIMBUSR-<user_id>/<uuid>/remove", methods=["DELETE"])
@login_required
def remove_sample_from_cart(uuid: str, user_id=None):
    sample_response = requests.get(
        url_for("api.sample_view_sample", uuid=uuid, _external=True),
        headers=get_internal_api_header(),
    )

    if sample_response.status_code == 200:
        remove_response = requests.delete(
            url_for(
                "api.remove_sample_from_cart",
                uuid=uuid,
                user_id=user_id,
                _external=True,
            ),
            headers=get_internal_api_header(),
        )

        return remove_response.content

    return sample_response.content


@sample.route("/cart/remove/LIMBRACK-<id>", methods=["GET"])
@sample.route("/cart/LIMBUSR-<user_id>/remove/LIMBRACK-<id>", methods=["GET"])
@login_required
def remove_rack_from_cart(id: int, user_id=None):
    sample_response = requests.get(
        url_for("api.storage_rack_view", id=id, _external=True),
        headers=get_internal_api_header(),
    )
    if sample_response.status_code == 200:
        remove_response = requests.delete(
            url_for(
                "api.remove_rack_from_cart", id=id, user_id=user_id, _external=True
            ),
            headers=get_internal_api_header(),
        )

        flash(remove_response.json()["message"])
        return redirect(url_for("sample.shipment_cart"))
    return sample_response.content


@sample.route("<uuid>/associate/document", methods=["GET", "POST"])
@login_required
def associate_document(uuid):

    sample_response = requests.get(
        url_for("api.sample_view_sample", uuid=uuid, _external=True),
        headers=get_internal_api_header(),
    )

    if sample_response.status_code == 200:
        document_response = requests.get(
            url_for("api.document_home", _external=True),
            headers=get_internal_api_header(),
        )

        if document_response.status_code == 200:

            form = SampleToDocumentAssociatationForm(
                document_response.json()["content"]
            )

            if form.validate_on_submit():

                response = requests.post(
                    url_for("api.sample_to_document", _external=True),
                    headers=get_internal_api_header(),
                    json={
                        "sample_id": sample_response.json()["content"]["id"],
                        "document_id": form.documents.data,
                    },
                )

                if response.status_code == 200:
                    flash("Document successfully associated")
                else:
                    flash("We have a problem :( %s" % (response.json()))

                return redirect(url_for("sample.view", uuid=uuid))

            return render_template(
                "sample/associate/document.html",
                sample=sample_response.json()["content"],
                form=form,
            )

        return abort(document_response.status_code)

    return abort(sample_response.status_code)


@sample.route("<uuid>/edit/basic_info", methods=["GET", "POST"])
@login_required
def edit_sample_basic_info(uuid):

    sample_response = requests.get(
        url_for("api.sample_view_sample", uuid=uuid, _external=True),
        headers=get_internal_api_header(),
    )

    if sample_response.status_code != 200:
        return abort(sample_response.status_code)

    if sample_response.json()["content"]["is_locked"]:
        flash("Sample is locked!")
        return abort(sample_response.status_code)

    # print("sample", sample_response.text)

    data = sample_response.json()["content"]
    consent_id = data["consent_information"]["id"]

    consent_ids = []
    if data["consent_information"]["donor_id"] is None:
        consent_ids = [[consent_id, "LIMBDC-%s" % consent_id]]

    consent_response = requests.get(
        url_for("api.sample_get_consents", _external=True),
        headers=get_internal_api_header(),
    )

    if consent_response.status_code == 200:
        for consent in consent_response.json()["content"]:
            consent_ids.append([consent["id"], consent["label"]])

    sites_response = requests.get(
        url_for("api.site_home", _external=True), headers=get_internal_api_header()
    )

    if sites_response.status_code == 200:
        collection_sites = []
        for site in sites_response.json()["content"]:
            collection_sites.append([site["id"], site["name"]])
    else:
        flash("Error in getting site info!")
        return abort(sites_response.status_code)

    data.update({"consent_id": consent_id})  # data["consent_information"]["id"]})

    form = EditBasicForm(consent_ids, collection_sites, data=data)

    if form.validate_on_submit():
        sample_info = {
            "status": form.status.data,
            "barcode": form.barcode.data,
            "colour": form.colour.data,
            "biohazard_level": form.biohazard_level.data,
            "quantity": form.quantity.data,
            # "remaining_quantity": remaining_quantity
            "consent_id": form.consent_id.data,
            "site_id": form.site_id.data,
        }
        response = requests.put(
            url_for("api.sample_edit_basic_info", uuid=uuid, _external=True),
            headers=get_internal_api_header(),
            json=sample_info,
        )

        if response.status_code == 200:
            flash(
                response.json()["message"]
                + "  Sample collection information successfully edited!"
            )

        else:
            flash(response.json()["message"])

        return redirect(url_for("sample.view", uuid=uuid))

    return render_template(
        "sample/edit.html",
        sample=sample_response.json()["content"],
        form=form,
    )


@sample.route("<uuid>/data", methods=["GET"])
@login_required
def view_data(uuid: str):
    sample_response = requests.get(
        url_for("api.sample_view_sample", uuid=uuid, _external=True),
        headers=get_internal_api_header(),
    )

    if sample_response.status_code == 200:
        return sample_response.json()
    return sample_response.content


@sample.route("<uuid>/update_status", methods=["GET"])
@login_required
def update_sample_status(uuid: str):
    sample_response = requests.get(
        url_for("api.sample_update_sample_status", uuid=uuid, _external=True),
        headers=get_internal_api_header(),
    )

    if sample_response.status_code == 200:
        flash("Success!" + sample_response.json()["message"])
    else:
        flash(sample_response.json()["message"])

    return redirect(url_for("sample.view", uuid=uuid))


@sample.route("<uuid>/remove", methods=["GET", "POST"])
@login_required
def remove_sample(uuid: str, user_id=None):
    sample_response = requests.get(
        url_for("api.sample_view_sample", uuid=uuid, _external=True),
        headers=get_internal_api_header(),
    )

    if sample_response.status_code == 200:
        remove_response = requests.delete(
            url_for(
                "api.sample_remove_sample", uuid=uuid, user_id=user_id, _external=True
            ),
            headers=get_internal_api_header(),
        )

        if remove_response.status_code == 200:
            flash(remove_response.json()["message"])
            # return redirect(url_for("sample.index"))
        else:
            flash(remove_response.json()["message"])
            # return redirect(url_for("sample.view", uuid=uuid))

        return remove_response.json()

    flash(sample_response.json()["message"])
    return sample_response.json()
    # return redirect(url_for("sample.view", uuid=uuid))


@sample.route("<uuid>/deep_remove", methods=["GET", "POST"])
@login_required
def deep_remove_sample(uuid: str):
    sample_response = requests.get(
        url_for("api.sample_view_sample", uuid=uuid, _external=True),
        headers=get_internal_api_header(),
    )

    if sample_response.status_code == 200:
        remove_response = requests.delete(
            url_for("api.sample_deep_remove_sample", uuid=uuid, _external=True),
            headers=get_internal_api_header(),
        )

        if remove_response.status_code == 200:
            flash(remove_response.json()["message"])
            # return redirect(url_for("sample.index"))
        else:
            flash(remove_response.json()["message"])
            # return redirect(url_for("sample.view", uuid=uuid))

        return remove_response.json()

    flash(sample_response.json()["message"])
    return sample_response.json()
    # return redirect(url_for("sample.view", uuid=uuid))
