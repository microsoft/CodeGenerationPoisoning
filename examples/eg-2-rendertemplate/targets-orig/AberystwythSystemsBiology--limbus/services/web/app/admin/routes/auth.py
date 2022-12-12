# Copyright (C) 2020  Keiron O'Shea <keo7@aber.ac.uk>
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

from .. import admin
from ...decorators import check_if_admin
from ...misc import get_internal_api_header

from ...auth.forms import UserAccountRegistrationForm, UserAccountEditForm
from ..forms import AdminUserAccountEditForm
from ..forms.auth import AccountLockPasswordForm

from flask import render_template, url_for, redirect, abort, flash, current_app
from flask_login import current_user, login_required

from ...extensions import mail

import requests

from flask_mail import Message


@admin.route("/auth/", methods=["GET"])
@check_if_admin
@login_required
def auth_index():
    return render_template("admin/auth/index.html")


@admin.route("/auth/new", methods=["GET", "POST"])
@check_if_admin
@login_required
def auth_new_account():
    sites_response = requests.get(
        url_for("api.site_home", _external=True), headers=get_internal_api_header()
    )

    if sites_response.status_code == 200:
        sites = []

        for site in sites_response.json()["content"]:
            sites.append(
                [int(site["id"]), "LIMBSIT-%s: %s" % (site["id"], site["name"])]
            )

        form = UserAccountRegistrationForm(sites, with_type=True)

        if form.validate_on_submit():

            new_user_response = requests.post(
                url_for("api.auth_new_user", _external=True),
                json={
                    "title": form.title.data,
                    "first_name": form.first_name.data,
                    "middle_name": form.middle_name.data,
                    "last_name": form.last_name.data,
                    "email": form.email.data,
                    "account_type": form.type.data,
                    "password": form.password.data,
                    "site_id": form.site.data,
                },
                headers=get_internal_api_header(),
            )

            if new_user_response.status_code == 200:
                flash("User successfully added!")
                return redirect(url_for("admin.auth_index"))
            else:
                flash("We have encountered a problem :(")

        return render_template("/admin/auth/new.html", form=form)
    else:
        return abort(500)


@admin.route("/auth/<id>", methods=["GET", "POST"])
@check_if_admin
@login_required
def auth_view_account(id):
    response = requests.get(
        url_for("api.auth_view_user", id=id, _external=True),
        headers=get_internal_api_header(),
    )

    if response.status_code == 200:
        form = AccountLockPasswordForm(response.json()["content"]["email"])

        if form.validate_on_submit():

            lock_response = requests.put(
                url_for("api.auth_lock_user", id=id, _external=True),
                headers=get_internal_api_header(),
            )

            if lock_response.status_code == 200:
                if lock_response.json()["content"]["is_locked"]:
                    flash("User Account locked!")
                else:
                    flash("User Account unlocked!")
                return redirect(url_for("admin.auth_index"))
            else:
                flash("We were unable to unlock the User Account.")

        return render_template(
            "admin/auth/view.html", user=response.json()["content"], form=form
        )
    else:
        return abort(response.status_code)


@admin.route("/auth/data", methods=["GET"])
@check_if_admin
@login_required
def auth_data():
    auth_response = requests.get(
        url_for("api.auth_home", _external=True),
        headers=get_internal_api_header(),
    )

    sites_response = requests.get(
        url_for("api.site_home_tokenuser", _external=True),
        headers=get_internal_api_header(),
    )

    if sites_response.status_code == 200:
        sites = sites_response.json()["content"]["choices"]
        sites_dict = {s[0]: s[1] for s in sites}
    else:
        sites_dict = None

    if auth_response.status_code == 200:
        auth_info = auth_response.json()["content"]

        for user in auth_info:
            # Default
            try:
                user["affiliated_site"] = sites_dict[user["site_id"]]
                user["working_sites"] = [user["affiliated_site"]]
            except:
                user["affiliated_site"] = user["site_id"]
                user["working_sites"] = [user["site_id"]]

            try:
                if "view_only" in user["settings"]:
                    entry_key = "view_only"
                elif "data_entry" in user["settings"]:
                    entry_key = "data_entry"
                else:
                    entry_key = None
                if entry_key:
                    user["working_sites"] = [
                        sites_dict[s]
                        for s in user["settings"][entry_key]["site"]["choices"]
                    ]

            except:
                pass
        # print("auth_info_final", auth_info)
        return {"content": auth_info, "success": True}

    return auth_response.content


@admin.route("/auth/<id>/password/reset", methods=["GET", "POST"])
@check_if_admin
@login_required
def admin_password_reset(id):
    response = requests.get(
        url_for("api.auth_view_user", id=id, _external=True),
        headers=get_internal_api_header(),
    )

    if response.status_code == 200:
        form = AccountLockPasswordForm(response.json()["content"]["email"])

        if form.validate_on_submit():

            token_email = requests.post(
                url_for("api.auth_password_reset", _external=True),
                headers=get_internal_api_header(),
                json={"email": form.email.data},
            )

            if token_email.status_code == 200:
                token = token_email.json()["content"]["token"]
                confirm_url = url_for(
                    "auth.change_password_external", token=token, _external=True
                )
                template = render_template(
                    "admin/auth/email/password_reset.html", reset_url=confirm_url
                )
                subject = "LIMBUS: Password Reset Email"
                msg = Message(
                    subject,
                    recipients=[form.email.data],
                    html=template,
                    sender=current_app.config["MAIL_USERNAME"],
                )
                mail.send(msg)
                flash("Password reset email has been sent!")
                return redirect(url_for("admin.auth_view_account", id=id))
            else:
                flash(token_email["content"])

        return render_template(
            "admin/auth/password_reset.html", user=response.json()["content"], form=form
        )
    else:
        return abort(response.status_code)


@admin.route("/auth/<id>/edit", methods=["GET", "POST"])
@check_if_admin
@login_required
def admin_edit_account(id):

    response = requests.get(
        url_for("api.auth_view_user", id=id, _external=True),
        headers=get_internal_api_header(),
    )

    sites_response = requests.get(
        url_for("api.site_home_tokenuser", _external=True),
        headers=get_internal_api_header(),
    )
    # sites=[0, None]
    if sites_response.status_code == 200:
        sites = sites_response.json()["content"]["choices"]
    else:
        flash("No site created!")
        return render_template(
            "admin/auth/edit.html", user=response.json()["content"], form={}
        )

    if response.status_code == 200:
        account_data = response.json()["content"]
        site_id = int(account_data["site"]["id"])
        account_data.update({"site_id": site_id})

        default_sites = [site_id]
        # -- prepare data population to the form
        # -- currently only either "data_entry" or "view_only", not both can be stored in the DB
        if "settings" in account_data and account_data["settings"] is not None:
            settings = []
            for access_type in account_data["settings"]:
                setting = {}
                if access_type == "data_entry":
                    setting["access_level"] = 1
                else:  # if access_type == "view_only":
                    setting["access_level"] = 2

                try:
                    setting["site_choices"] = account_data["settings"][access_type][
                        "site"
                    ]["choices"]
                    if (
                        setting["site_choices"] is None
                        or len(setting["site_choices"]) == 0
                    ):
                        setting["site_choices"] = default_sites
                except:
                    setting["site_choices"] = default_sites

                setting["site_selected"] = "\n".join(
                    [s[1] for s in sites if s[0] in setting["site_choices"]]
                )
                settings.append(setting)

            account_data["settings"] = settings
        else:
            account_data["settings"] = [
                {
                    "access_level": 1,
                    "site_choices": default_sites,
                    "site_selected": [s[1] for s in sites if s[0] == site_id][0],
                }
            ]

        print("account_data", account_data)
        print("setting", account_data["settings"])

        form = AdminUserAccountEditForm(sites=sites, data=account_data)
        for setting in form.settings.entries:
            setting.site_choices.choices = sites

        if form.validate_on_submit():
            json = {
                "title": form.title.data,
                "first_name": form.first_name.data,
                "middle_name": form.middle_name.data,
                "last_name": form.last_name.data,
                "email": form.email.data,
                "account_type": form.account_type.data,
                # "password": form.password.data,
                "site_id": form.site_id.data,
            }

            settings = {}
            for setting in form.settings.entries:
                print("setting : ", setting.site_choices.data)
                site_choices = []
                if len(setting.site_choices.data) > 0:
                    site_choices = [
                        int(k)
                        for k in setting.site_choices.data
                        if int(k) != account_data["site_id"]
                    ]
                    site_choices = [account_data["site_id"]] + site_choices

                if setting.access_level.data == 2:
                    settings["view_only"] = {"site": {"choices": site_choices}}
                else:
                    settings["data_entry"] = {"site": {"choices": site_choices}}

            json["settings"] = settings

            print("json", json)
            edit_response = requests.put(
                url_for("api.admin_edit_account", id=id, _external=True),
                headers=get_internal_api_header(),
                json=json,
            )
            print("edit_response", edit_response.text)
            if edit_response.status_code == 200:
                flash("User account updated successfully!")
                return redirect(url_for("admin.auth_view_account", id=id))
            else:
                flash(edit_response.json()["message"])

        return render_template(
            "admin/auth/edit.html", user=response.json()["content"], form=form
        )
    else:
        return abort(response.status_code)
