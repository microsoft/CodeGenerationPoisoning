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

from flask import render_template, url_for, flash, redirect

from flask_login import login_required

from . import protocol

from ..misc import get_internal_api_header
import requests

from .forms import ProtocolCreationForm, MdeForm, DocumentAssociationForm


@login_required
@protocol.route("/")
def index():
    response = requests.get(
        url_for("api.protocol_home", _external=True), headers=get_internal_api_header()
    )

    if response.status_code == 200:
        return render_template(
            "protocol/index.html", protocols=response.json()["content"]
        )
    else:
        return response.content


@login_required
@protocol.route("/new", methods=["GET", "POST"])
def new():
    form = ProtocolCreationForm()
    if form.validate_on_submit():
        protocol_information = {
            "name": form.name.data,
            "doi": form.doi.data,
            "description": form.description.data,
            "type": form.type.data,
        }

        response = requests.post(
            url_for("api.protocol_new_protocol", _external=True),
            headers=get_internal_api_header(),
            json=protocol_information,
        )

        if response.status_code == 200:
            flash("Protocol Successfully Created")
            return render_template(
                "protocol/view.html", protocol=response.json()["content"]
            )
        else:
            flash("Error: %s - %s" % (response.status_code, response.json()))

    return render_template("protocol/new.html", form=form)


@protocol.route("/LIMBPRO-<id>")
@login_required
def view(id):
    response = requests.get(
        url_for("api.protocol_view_protocol", id=id, _external=True),
        headers=get_internal_api_header(),
    )
    if response.status_code == 200:
        return render_template(
            "protocol/view.html", protocol=response.json()["content"]
        )
    else:
        return response.content


@protocol.route("/LIMBPRO-<id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    response = requests.get(
        url_for("api.protocol_view_protocol", id=id, _external=True),
        headers=get_internal_api_header(),
    )

    if response.status_code == 200:
        print("response.json()", response.json()["content"])
        form = ProtocolCreationForm(data=response.json()["content"])
        del form.type

        if form.validate_on_submit():
            protocol_information = {
                "name": form.name.data,
                "description": form.description.data,
                "doi": form.doi.data,
            }

            edit_response = requests.put(
                url_for("api.protocol_edit_protocol", id=id, _external=True),
                headers=get_internal_api_header(),
                json=protocol_information,
            )

            if edit_response.status_code == 200:
                flash("Protocol Successfully Edited")
                return redirect(url_for("protocol.view", id=id))
            else:
                flash("Error: %s" % response.json())
        return render_template(
            "protocol/edit.html", protocol=response.json()["content"], form=form
        )
    else:
        return response.content


@protocol.route("/LIMBPRO-<id>/associate_document", methods=["GET", "POST"])
@login_required
def associate_document(id):
    response = requests.get(
        url_for("api.protocol_view_protocol", id=id, _external=True),
        headers=get_internal_api_header(),
    )
    if response.status_code == 200:
        form = DocumentAssociationForm()
        if form.validate_on_submit():
            association_information = {
                "document_id": form.document.data,
                "protocol_id": id,
                "description": form.description.data,
            }

            association_request = requests.post(
                url_for("api.protocol_associate_document", id=id, _external=True),
                headers=get_internal_api_header(),
                json=association_information,
            )

            if association_request.status_code == 200:
                flash("Association Successfully Createed")
                return redirect(url_for("protocol.view", id=id))
            else:
                flash("Error: %s" % response.json())

        return render_template(
            "protocol/document_association.html",
            protocol=response.json()["content"],
            form=form,
        )
    else:
        return response.content


@protocol.route("/LIMBPRO-<id>/add", methods=["GET", "POST"])
@login_required
def new_text(id):
    response = requests.get(
        url_for("api.protocol_view_protocol", id=id, _external=True),
        headers=get_internal_api_header(),
    )
    if response.status_code == 200:
        form = MdeForm()
        if form.validate_on_submit():
            text_information = {"type": form.type.data, "text": form.editor.data}

            response = requests.post(
                url_for("api.protocol_new_protocol_text", id=id, _external=True),
                headers=get_internal_api_header(),
                json=text_information,
            )

            if response.status_code == 200:
                flash("Protocol Text Successfully Created")
                return redirect(url_for("protocol.view", id=id))
            else:
                flash("Error: %s - %s" % (response.status_code))
        return render_template(
            "protocol/new_text.html", form=form, protocol=response.json()["content"]
        )
    else:
        return response.content


@protocol.route("/LIMBPRO-<id>/remove", methods=["GET", "POST"])
@login_required
def remove(id):
    remove_response = requests.post(
        url_for("api.protocol_remove_protocol", id=id, _external=True),
        headers=get_internal_api_header(),
    )

    if remove_response.status_code == 200:
        flash("Protocol Successfully Deleted")
    else:
        flash(remove_response.json()["message"])
    return remove_response.json()
