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

from .models import *

import requests
from ..misc import get_internal_api_header
from . import procedure
from .forms import (
    DiagnosticProcedureClassCreationForm,
    DiagnosticProcedureCreationForm,
    DiagnosticProcedureVolumeCreationForm,
    DiagnosticProcedureSubVolumeCreationForm,
)

import json


@procedure.route("/")
@login_required
def index():

    response = requests.get(
        url_for("api.procedure_home", _external=True), headers=get_internal_api_header()
    )

    if response.status_code == 200:
        return render_template(
            "procedure/index.html", procedures=response.json()["content"]
        )

    abort(response.status_code)


@procedure.route("/view/LIMBDIAG-<id>/tree")
@login_required
def view_tree(id):

    response = requests.get(
        url_for("api.procedure_tree", id=id, _external=True),
        headers=get_internal_api_header(),
    )

    if response.status_code == 200:
        return response.json()
    abort(response.status_code)


@procedure.route("/view/LIMBDIAG-<id>")
@login_required
def view(id):
    return render_template("procedure/view.html")


@procedure.route("/view/LIMBDIAG-<id>/endpoint")
@login_required
def view_class_endpoint(id):
    response = requests.get(
        url_for("api.procedure_view_class", id=id, _external=True),
        headers=get_internal_api_header(),
    )

    if response.status_code == 200:
        return response.json()

    abort(response.status_code)


@procedure.route("/view/LIMBDIAG-<id>/volume/new", methods=["GET", "POST"])
@login_required
def new_volume(id):
    response = requests.get(
        url_for("api.procedure_view_class", id=id, _external=True),
        headers=get_internal_api_header(),
    )

    if response.status_code == 200:
        form = DiagnosticProcedureVolumeCreationForm()

        if form.validate_on_submit():

            volume_response = requests.post(
                url_for("api.procedure_new_volume", _external=True),
                headers=get_internal_api_header(),
                json={
                    "code": form.code.data,
                    "name": form.name.data,
                    "class_id": response.json()["content"]["id"],
                },
            )

            if volume_response.status_code == 200:
                flash("Volume successfully added")
                return redirect(
                    url_for("procedure.view", id=response.json()["content"]["id"])
                )

            flash("Error")

        return render_template(
            "procedure/new/volume.html", pclass=response.json()["content"], form=form
        )

    else:
        abort(response.status_code)


@procedure.route("/new/volume/<id>/subvolume/new", methods=["GET", "POST"])
@login_required
def new_subvolume(id):
    response = requests.get(
        url_for("api.procedure_view_volume", id=id, _external=True),
        headers=get_internal_api_header(),
    )

    if response.status_code == 200:

        form = DiagnosticProcedureSubVolumeCreationForm()

        if form.validate_on_submit():
            new_response = requests.post(
                url_for("api.procedure_new_subvolume", _external=True),
                headers=get_internal_api_header(),
                json={"code": form.code.data, "name": form.name.data, "volume_id": id},
            )

            if new_response.status_code == 200:
                flash("Subvolume added")

            else:
                flash("Oh no...")

        return render_template(
            "procedure/new/subvolume.html", volume=response.json()["content"], form=form
        )

    abort(response.status_code)


@procedure.route("/new/procedure/<id>", methods=["GET", "POST"])
@login_required
def new_procedure(id):
    response = requests.get(
        url_for("api.procedure_view_subvolume", id=id, _external=True),
        headers=get_internal_api_header(),
    )

    if response.status_code == 200:
        form = DiagnosticProcedureCreationForm()

        return render_template(
            "procedure/new/procedure.html",
            form=form,
            subvolume=response.json()["content"],
        )

    abort(response.status_code)


@procedure.route("/view/volume/<id>/endpoint")
@login_required
def view_volume_endpoint(id):
    response = requests.get(
        url_for("api.procedure_view_volume", id=id, _external=True),
        headers=get_internal_api_header(),
    )

    if response.status_code == 200:
        return response.json()

    abort(response.status_code)


@procedure.route("/view/subvolume/<id>/endpoint")
@login_required
def view_subvolume_endpoint(id):
    response = requests.get(
        url_for("api.procedure_view_subvolume", id=id, _external=True),
        headers=get_internal_api_header(),
    )

    if response.status_code == 200:
        return response.json()

    abort(response.status_code)


@procedure.route("/new", methods=["GET", "POST"])
def new():
    form = DiagnosticProcedureClassCreationForm()

    if form.validate_on_submit():
        new_response = requests.post(
            url_for("api.procedure_new_class", _external=True),
            json={
                "name": form.name.data,
                "description": form.description.data,
                "version": form.version.data,
            },
            headers=get_internal_api_header(),
        )

        if new_response.status_code == 200:
            flash("Procedure class successfuly added.")
            return redirect(
                url_for("procedure.view", id=new_response.json()["content"]["id"])
            )
        else:
            flash("We have a problem!")
    return render_template("procedure/new/class.html", form=form)
