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
    render_template,
    url_for,
    abort,
    current_app,
    send_file,
    session,
    flash,
)
from flask_login import login_required, current_user

import io

from . import document
from .forms import (
    DocumentCreationForm,
    DocumentLockForm,
    UploadFileForm,
    DocumentFileDeletionForm,
)

from ..misc import get_internal_api_header
import requests
import re


@login_required
@document.route("/")
def index():
    response = requests.get(
        url_for("api.document_home", _external=True), headers=get_internal_api_header()
    )

    if response.status_code == 200:
        return render_template(
            "document/index.html", documents=response.json()["content"]
        )
    else:
        return abort(response.status_code)


@document.route("/new", methods=["GET", "POST"])
@login_required
def new_document():
    form = DocumentCreationForm()
    if form.validate_on_submit():

        document_information = {
            "name": form.name.data,
            "description": form.description.data,
            "type": form.type.data,
        }

        response = requests.post(
            url_for("api.document_new_document", _external=True),
            headers=get_internal_api_header(),
            json=document_information,
        )

        if response.status_code == 200:

            file_response = requests.post(
                url_for(
                    "api.document_upload_file",
                    id=int(response.json()["content"]["id"]),
                    _external=True,
                ),
                headers=get_internal_api_header(),
                params={"filename": form.file.data.filename},
                data=form.file.data,
            )

            if file_response.status_code == 200:
                flash("Document Successfully Created")

                return redirect(
                    url_for("document.view", id=response.json()["content"]["id"])
                )

            else:
                flash("We have a problem", file_response.json())
        else:
            return abort(response.status_code)

    return render_template("document/upload/index.html", form=form)


@document.route("/LIMBDOC-<id>")
@login_required
def view(id):

    response = requests.get(
        url_for("api.document_view_document", id=id, _external=True),
        headers=get_internal_api_header(),
    )
    if response.status_code == 200:
        form = DocumentLockForm(id)
        return render_template(
            "document/view.html", document=response.json()["content"], form=form
        )
    else:
        return abort(response.status_code)


@document.route("/LIMBDOC-<id>/lock", methods=["POST"])
@login_required
def lock(id):
    form = DocumentLockForm(id)
    if form.validate_on_submit():
        response = requests.get(
            url_for("api.document_view_document", id=id, _external=True),
            headers=get_internal_api_header(),
        )
        if response.status_code == 200:
            lock_response = requests.put(
                url_for("api.document_lock_document", id=id, _external=True),
                headers=get_internal_api_header(),
            )
            if lock_response.status_code == 200:
                flash("Document Successfully Locked")
                return redirect(url_for("document.index"))
            else:
                flash("We have a problem: %s" % (lock_response.json()))

    else:
        return redirect(url_for("document.view", id=id))


@document.route("/LIMBDOC-<id>/file/new", methods=["GET", "POST"])
@login_required
def new_file(id):
    response = requests.get(
        url_for("api.document_view_document", id=id, _external=True),
        headers=get_internal_api_header(),
    )
    if response.status_code == 200:
        form = UploadFileForm()
        if form.validate_on_submit():

            response = requests.post(
                url_for("api.document_upload_file", id=id, _external=True),
                headers=get_internal_api_header(),
                params={"filename": form.file.data.filename},
                data=form.file.data,
            )

            if response.status_code == 200:
                return redirect(url_for("document.view", id=id))
            else:
                return response.content
        else:
            return render_template(
                "document/upload/upload.html",
                document=response.json()["content"],
                form=form,
            )
    else:
        return abort(response.status_code)


@document.route("/LIMBDOC-<id>/edit", methods=["GET", "POST"])
@login_required
def edit(id):
    response = requests.get(
        url_for("api.document_view_document", id=id, _external=True),
        headers=get_internal_api_header(),
    )
    if response.status_code == 200:
        form = DocumentCreationForm(data=response.json()["content"])

        if form.validate_on_submit():
            form_information = {
                "name": form.name.data,
                "type": form.type.data,
                "description": form.description.data,
            }

            edit_response = requests.put(
                url_for("api.document_edit_document", id=id, _external=True),
                headers=get_internal_api_header(),
                json=form_information,
            )

            if edit_response.status_code == 200:
                flash("Document Successfully Edited")
            else:
                flash("We have a problem: %s" % (edit_response.json()))
            return redirect(url_for("document.view", id=id))
        return render_template(
            "document/edit.html", document=response.json()["content"], form=form
        )
    else:
        return response.content


@document.route("/LIMBDOC-<id>/file/<file_id>/get")
@login_required
def view_file(id, file_id):
    response = requests.get(
        url_for("api.document_file_get", id=id, file_id=file_id, _external=True),
        headers=get_internal_api_header(),
    )

    if response.status_code == 200:
        d = response.headers["content-disposition"]
        fname = re.findall("filename=(.+)", d)[0]
        return (
            send_file(
                io.BytesIO(response.content),
                as_attachment=True,
                attachment_filename=fname,
            ),
            200,
        )
    else:
        return response.content


@document.route("/LIMBDOC-<id>/file/<file_id>/remove", methods=["GET", "POST"])
@login_required
def remove_file(id, file_id):

    document_response = requests.get(
        url_for("api.document_view_document", id=id, _external=True),
        headers=get_internal_api_header(),
    )

    if document_response.status_code == 200:

        response = requests.get(
            url_for("api.document_file_view", id=id, file_id=file_id, _external=True),
            headers=get_internal_api_header(),
        )

        if response.status_code == 200:

            form = DocumentFileDeletionForm(response.json()["content"]["name"])

            if form.validate_on_submit():
                remove_response = requests.delete(
                    url_for(
                        "api.document_file_remove",
                        id=id,
                        file_id=file_id,
                        _external=True,
                    ),
                    headers=get_internal_api_header(),
                )

                if remove_response.status_code == 200:
                    flash("Document File Successfully Removed")
                    return redirect(url_for("document.view", id=id))
                else:
                    flash(remove_response.json()["content"])

            return render_template(
                "document/file/remove.html",
                document=document_response.json()["content"],
                file=response.json()["content"],
                form=form,
            )
        else:
            return response.content
    else:
        return document_response.content
