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

from . import tmpstore

from flask import render_template, url_for, abort
from flask_login import login_required, current_user

import requests
from ..misc import get_internal_api_header

import json


@tmpstore.route("/", methods=["GET"])
@login_required
def index():
    tmpstore_response = requests.get(
        url_for("api.tmpstore_home", _external=True), headers=get_internal_api_header()
    )

    if tmpstore_response.status_code != 200:
        abort(tmpstore.status_code)

    return render_template(
        "/tmpstore/index.html", tmpstores=tmpstore_response.json()["content"]
    )


@tmpstore.route("/view/<hash>", methods=["GET"])
@login_required
def view(hash: str):
    tmpstore_response = requests.get(
        url_for("api.tmpstore_view_tmpstore", hash=hash, _external=True),
        headers=get_internal_api_header(),
    )

    if tmpstore_response.status_code != 200:
        abort(tmpstore.status_code)

    return render_template(
        "/tmpstore/view.html",
        hash=hash,
        tmpstore=json.dumps(tmpstore_response.json()["content"], indent=4),
    )
