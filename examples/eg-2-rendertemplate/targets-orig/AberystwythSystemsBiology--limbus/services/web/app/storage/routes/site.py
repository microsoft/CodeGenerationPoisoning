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
    flash,
)

from flask_login import current_user, login_required
from .. import storage
import requests
from ...misc import get_internal_api_header
from ..forms import SiteEditForm, SiteAddressEditForm

from ...decorators import check_if_admin


@storage.route("/site/LIMBSITE-<id>", methods=["GET"])
@login_required
def view_site(id):
    response = requests.get(
        url_for("api.site_view", id=id, _external=True),
        headers=get_internal_api_header(),
        # json={"is_locked": False},
    )

    if response.status_code == 200:
        site_info = response.json()["content"]

        site_info["type"] = "Internal"
        if "is_external" in site_info and site_info["is_external"]:
            site_info["type"] = "External"

        return render_template("storage/site/view.html", site=site_info)

    return abort(response.status_code)


@storage.route("/site/LIMBSITE-<id>/delete", methods=["GET", "POST"])
@login_required
def delete_site(id):

    response = requests.get(
        url_for("api.site_view", id=id, _external=True),
        headers=get_internal_api_header(),
    )

    if response.json()["content"]["is_locked"]:
        return abort(401)

    if response.status_code == 200:
        edit_response = requests.put(
            url_for("api.storage_site_delete", id=id, _external=True),
            headers=get_internal_api_header(),
        )

        if edit_response.status_code == 200:
            flash("Site Successfully Deleted")
            return redirect(url_for("storage.index", _external=True))

        else:
            flash(edit_response.json()["message"])
        return redirect(url_for("storage.view_site", id=id, _external=True))
    return abort(response.status_code)


@storage.route("/site/LIMBSITE-<id>/lock", methods=["GET", "POST"])
@login_required
@check_if_admin
def lock_site(id):

    edit_response = requests.put(
        url_for("api.storage_site_lock", id=id, _external=True),
        headers=get_internal_api_header(),
    )

    if edit_response.status_code == 200:
        if edit_response.json()["content"]:
            flash("Site Successfully Locked")
        else:
            flash("Site Successfully Unlocked")
    else:
        flash("We have a problem: %s" % (edit_response.status_code))

    return redirect(url_for("storage.view_site", id=id))

    return abort(response.status_code)


@storage.route("/site/LIMBSITE-<id>/edit", methods=["GET", "POST"])
@login_required
def edit_site(id):

    response = requests.get(
        url_for("api.site_view", id=id, _external=True),
        headers=get_internal_api_header(),
    )

    if response.json()["content"]["is_locked"]:
        flash("The site is locked!")
        return redirect(url_for("storage.view_site", id=id))

    if response.status_code == 200:

        site_info = response.json()["content"]["address"]
        for k in ["name", "description", "url", "is_external"]:
            site_info[k] = response.json()["content"][k]
        site_info.pop("id")

        form = SiteEditForm(data=site_info)

        if form.validate_on_submit():
            form_information = {
                "name": form.name.data,
                "description": form.description.data,
                "url": form.url.data,
                "address": {
                    "street_address_one": form.street_address_one.data,
                    "street_address_two": form.street_address_two.data,
                    "city": form.city.data,
                    "county": form.county.data,
                    "post_code": form.post_code.data,
                    "country": form.country.data,
                },
                "is_external": form.is_external.data,
            }

            edit_response = requests.put(
                url_for("api.storage_site_edit", id=id, _external=True),
                headers=get_internal_api_header(),
                json=form_information,
            )

            if edit_response.status_code == 200:
                flash("Site Successfully Edited")
            else:
                flash("We have a problem: %s" % (edit_response.json()))

            return redirect(url_for("storage.view_site", id=id))

        return render_template(
            "storage/site/edit.html", room=response.json()["content"], form=form
        )

    return abort(response.status_code)


@storage.route("/site/LIMBSITE-<id>/edit_addresses", methods=["GET", "POST"])
@login_required
def site_edit_addresses(id):
    response = requests.get(
        url_for("api.site_addresses_view", id=id, _external=True),
        headers=get_internal_api_header(),
    )

    if response.json()["content"]["is_locked"]:
        flash("The site is locked!")
        return redirect(url_for("storage.view_site", id=id))

    if response.status_code != 200:
        flash("Error in retrieving site address info!")
        return redirect(url_for("storage.view_site", id=id))

    site_info = response.json()["content"]
    site_info["id"] = id
    site_info["num_addresses"] = len(site_info["addresses"])

    addr0 = []
    addr1 = []
    for address in site_info["addresses"]:
        address["address_id"] = address["id"]
        address["delete"] = False
        if address["id"] == site_info["address_id"]:
            address["is_default"] = True
            addr0.append(address)
        else:
            address["is_default"] = False
            addr1.append(address)

    # - default address first
    site_info["addresses"] = addr0 + addr1

    form = SiteAddressEditForm(site_info)
    address_id = site_info["address_id"]

    if form.validate_on_submit():

        addresses = []
        new = []
        address_id = site_info["address_id"]
        for addr in form.addresses.entries:
            # address = eval(str(addr.data))
            # address.pop("csrf_token", None)
            address = {
                "id": addr.address_id.data,
                "street_address_one": addr.street_address_one.data,
                "street_address_two": addr.street_address_two.data,
                "city": addr.city.data,
                "county": addr.county.data,
                "country": addr.country.data,
                "post_code": addr.post_code.data,
                "is_default": addr.is_default.data,
                "delete": addr.delete.data,
                "site_id": id,
            }
            # print("address: ", address)

            if address["id"] in [None, ""]:
                if address["delete"]:
                    continue
                new.append(address)
            else:
                addresses.append(address)

            if address["is_default"]:
                address_id = address["id"]

        form_information = {
            "name": form.name.data,
            "description": form.description.data,
            "url": form.url.data,
            "address_id": address_id,
            "addresses": addresses,
            "new_addresses": new,
            "is_external": form.is_external.data,
        }

        # print("form_informationn", form_information)
        edit_addresses_request = requests.post(
            url_for("api.site_edit_addresses", id=id, _external=True),
            headers=get_internal_api_header(),
            json=form_information,
        )

        if edit_addresses_request.status_code == 200:
            flash("Site info and addresses updated successfully! ")
        else:
            flash(edit_addresses_request.json()["message"])

        return redirect(url_for("storage.view_site", id=id))

    else:
        print(form.errors)
        if form.errors != {}:
            flash("Form validation errors!" + str(form.errors))

    return render_template(
        "/storage/site/edit_addresses.html", form=form, site=site_info
    )
