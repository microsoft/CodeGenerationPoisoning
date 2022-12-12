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

from . import donor

from flask import (
    redirect,
    render_template,
    url_for,
    abort,
    current_app,
    session,
    flash,
    request,
)
from flask_login import login_required, current_user
import requests
from datetime import datetime

from .forms import (
    DonorCreationForm,
    DonorFilterForm,
    DonorAssignDiagnosisForm,
    DonorSampleAssociationForm,
    ConsentTemplateSelectForm,
    ConsentAnswerForm,
    ConsentQuestionnaire,
    ConsentSelectForm,
    ConsentWithdrawalForm,
)

from ..sample.forms.new.one import CollectionDonorConsentAndDisposalForm
from ..sample.forms.new.three import SampleTypeSelectForm
from ..consent.models import ConsentFormTemplate, ConsentFormTemplateQuestion
from ..misc import get_internal_api_header

strconv = lambda i: i or None


@donor.route("/")
@login_required
def index() -> str:

    sites_response = requests.get(
        url_for("api.site_home_tokenuser", _external=True),
        headers=get_internal_api_header(),
    )

    if sites_response.status_code == 200:
        sites = sites_response.json()["content"]["choices"]
        user_site_id = sites_response.json()["content"]["user_site_id"]

    form = DonorFilterForm(sites, data={"enrollment_site_id": user_site_id})
    return render_template("donor/index.html", form=form)


@donor.route("/query", methods=["POST"])
@login_required
def query_index():
    response = requests.get(
        url_for("api.donor_query", _external=True),
        headers=get_internal_api_header(),
        json=request.json,
    )

    if response.status_code == 200:
        return response.json()
    else:
        abort(response.status_code)


@donor.route("/LIMBDON-<id>")
@login_required
def view(id):
    return render_template("donor/view.html")


@donor.route("/LIMBDON-<id>/endpoint")
@login_required
def view_endpoint(id):
    response = requests.get(
        url_for("api.donor_view", id=id, _external=True),
        headers=get_internal_api_header(),
    )

    if response.status_code == 200:
        return response.json()


@donor.route("/get_study_reference", methods=["POST"])
@login_required
def get_study_reference():
    response = requests.get(
        url_for("api.donor_study_reference", _external=True),
        headers=get_internal_api_header(),
        json=request.json,
    )
    if response.status_code == 200:
        return response.json()
    else:
        abort(response.status_code)


# TODO sample to donor association:
#  should done by sample basic edit and change the consent form
@donor.route("/LIMBDON-<id>/associate/sample", methods=["GET", "POST"])
@login_required
def associate_sample(id):
    response = requests.get(
        url_for("api.donor_view", id=id, _external=True),
        headers=get_internal_api_header(),
    )

    if response.status_code == 200:
        sample_response = requests.get(
            url_for("api.sample_query", _external=True),
            headers=get_internal_api_header(),
            json={"source": "NEW"},
        )

        if sample_response.status_code == 200:
            samples = []
            for sample in sample_response.json()["content"]:
                if sample["is_locked"]:
                    continue

                if (
                    sample["consent_information"]["donor_id"] is None
                    and sample["consent_information"]["withdrawn"] is False
                ):
                    samples.append(sample)

            form = DonorSampleAssociationForm(samples)

            if form.validate_on_submit():
                association_response = requests.post(
                    url_for("api.donor_associate_sample", id=id, _external=True),
                    headers=get_internal_api_header(),
                    json={"sample_id": form.sample.data},
                )

                if association_response.status_code == 200:
                    flash(association_response.json()["message"])
                    return redirect(url_for("donor.view", id=id))

                flash(association_response.json()["message"])

            return render_template(
                "donor/sample/associate.html",
                donor=response.json()["content"],
                form=form,
            )
        abort(sample_response.status_code)
    abort(response.status_code)


@donor.route("/LIMBDON-<id>/associate/diagnosis", methods=["GET", "POST"])
@login_required
def new_diagnosis(id):
    response = requests.get(
        url_for("api.donor_view", id=id, _external=True),
        headers=get_internal_api_header(),
    )

    if response.status_code == 200:

        form = DonorAssignDiagnosisForm()

        if form.validate_on_submit():

            diagnosis_response = requests.post(
                url_for("api.donor_new_diagnosis", id=id, _external=True),
                headers=get_internal_api_header(),
                json={
                    "doid_ref": form.disease_select.data,
                    "stage": form.stage.data,
                    "diagnosis_date": str(
                        datetime.strptime(
                            str(form.diagnosis_date.data), "%Y-%m-%d"
                        ).date()
                    ),
                    "comments": form.comments.data,
                },
            )

            if diagnosis_response.status_code == 200:
                flash("Disease Annotation Added!")
                return redirect(url_for("donor.view", id=id))

            flash("Error!: %s" % diagnosis_response.json()["message"])

        return render_template(
            "donor/diagnosis/assign.html", donor=response.json()["content"], form=form
        )
    else:
        return response.content


@donor.route("/LIMBDIAG-<id>/remove", methods=["GET", "POST"])
@login_required
def remove_diagnosis(id):
    remove_response = requests.delete(
        url_for("api.donor_remove_diagnosis", id=id, _external=True),
        headers=get_internal_api_header(),
    )

    if remove_response.status_code == 200:
        flash(remove_response.json()["message"])
    else:
        flash(remove_response.json()["message"])

    return remove_response.json()


@donor.route("/LIMBDON-<id>/new/consent", methods=["GET", "POST"])
@login_required
def new_consent(id):
    response = requests.get(
        url_for("api.donor_view", id=id, _external=True),
        headers=get_internal_api_header(),
    )

    if response.status_code == 200:
        consent_templates = []

        consent_templates_response = requests.get(
            url_for("api.consent_query_tokenuser", _external=True),
            headers=get_internal_api_header(),
            json={"is_locked": False},
        )

        if consent_templates_response.status_code == 200:
            consent_templates = consent_templates_response.json()["content"]["choices"]

        form = ConsentTemplateSelectForm(consent_templates)

        if form.validate_on_submit():
            return redirect(
                url_for(
                    "donor.add_consent_answers",
                    donor_id=id,
                    template_id=form.consent_select.data,
                )
            )

        return render_template(
            "donor/consent/new_consent.html",
            donor=response.json()["content"],
            form=form,
        )
    else:
        return response.content


@donor.route(
    "/LIMBDON-<donor_id>/new/digital_consent_form-<template_id>",
    methods=["GET", "POST"],
)
@login_required
def add_consent_answers(template_id, donor_id):
    consent_response = requests.get(
        url_for("api.consent_view_template", id=template_id, _external=True),
        headers=get_internal_api_header(),
    )

    if consent_response.status_code != 200:
        return consent_response.response

    consent_template = consent_response.json()["content"]
    consent_data = {
        "template_name": consent_template["name"],
        "template_version": consent_template["version"],
        "questions": consent_template["questions"],
    }

    protocols_response = requests.get(
        url_for("api.protocol_query_tokenuser", default_type="STU", _external=True),
        headers=get_internal_api_header(),
        json={"is_locked": False, "type": ["STU"]},
    )

    study_protocols = []
    if protocols_response.status_code == 200:
        study_protocols = protocols_response.json()["content"]["choices"]

    study_protocols = [(0, "--- Select a study ---")] + study_protocols

    form = ConsentQuestionnaire(study_protocols, data=consent_data)

    if form.validate_on_submit():
        consent_details = {
            "donor_id": donor_id,
            "identifier": form.identifier.data,
            "template_id": consent_template["id"],
            "comments": form.comments.data,
            "date": str(form.date.data),
            "undertaken_by": form.undertaken_by.data,
            "answers": [],
            "study_protocol_id": form.study_select.data,
            "study": form.study.data,
        }

        for question in consent_template["questions"]:
            if getattr(form, str(question["id"])).data:
                consent_details["answers"].append(question["id"])

        if form.study_select.data == 0:
            consent_details["study_protocol_id"] = None
            consent_details["study"] = None

        else:
            consent_details["study"]["event"] = {
                "datetime": str(
                    datetime.strptime(
                        "%s %s" % (consent_details["study"].pop("date"), "00:00:00"),
                        "%Y-%m-%d %H:%M:%S",
                    )
                ),
                "comments": consent_details["study"].pop("comments"),
                "undertaken_by": consent_details["study"].pop("undertaken_by"),
            }

        consent_response = requests.post(
            url_for("api.donor_new_consent", _external=True),
            headers=get_internal_api_header(),
            json=consent_details,
        )

        if consent_response.status_code == 200:
            flash("Donor consent added successfully!")
            return redirect(url_for("donor.view", id=donor_id))

        flash("We have a problem :( %s" % consent_response.json()["message"])

    return render_template(
        "donor/consent/donor_consent_answers.html",
        form=form,
        donor_id=donor_id,
        template_id=template_id,
    )


@donor.route("/sample/<sample_uuid>/consent/LIMBDC-<id>/edit", methods=["GET", "POST"])
@donor.route("/LIMBDON-<donor_id>/consent/LIMBDC-<id>/edit", methods=["GET", "POST"])
@login_required
def edit_donor_consent(id, donor_id=None, sample_uuid=None):

    consent_id = int(id)
    consent_response = requests.get(
        url_for("api.donor_consent_view", id=consent_id, _external=True),
        headers=get_internal_api_header(),
    )

    if consent_response.status_code != 200:
        return consent_response.response

    consent_info = consent_response.json()["content"]
    donor_id = consent_info["donor_id"]
    consent_info.update(
        {
            "template_id": consent_info["template"]["id"],
            "template_name": consent_info["template"]["name"],
            "template_version": consent_info["template"]["version"],
            "questions": consent_info.pop("template_questions"),
        }
    )

    consent_info["date"] = datetime.strptime(consent_info["date"], "%Y-%m-%d")

    try:
        consent_info["study_select"] = consent_info["study"]["protocol"]["id"]
        consent_info["study"]["event"]["date"] = datetime.strptime(
            consent_info["study"]["event"]["datetime"], "%Y-%m-%dT%H:%M:%S"
        ).date()

        consent_info["study"].update(consent_info["study"].pop("event"))

    except:
        consent_info["study_select"] = None
        consent_info.pop("study", None)

    for question in consent_info["questions"]:
        checked = [a["id"] for a in consent_info["answers"]]
        if question["id"] in checked:
            question["checked"] = "checked"
        else:
            question["checked"] = ""

    protocols_response = requests.get(
        url_for("api.protocol_query_tokenuser", default_type="STU", _external=True),
        headers=get_internal_api_header(),
        json={"is_locked": False, "type": ["STU"]},
    )

    study_protocols = []
    if protocols_response.status_code == 200:
        study_protocols = protocols_response.json()["content"]["choices"]

    study_protocols = [(0, "--- Select a study ---")] + study_protocols

    template_id = consent_info["id"]

    form = ConsentQuestionnaire(study_protocols, data=consent_info)

    if form.validate_on_submit():
        consent_details = {
            "donor_id": donor_id,
            "identifier": form.identifier.data,
            "template_id": consent_info["template_id"],
            "comments": form.comments.data,
            "date": str(form.date.data),
            "undertaken_by": form.undertaken_by.data,
            "answers": [],
            "study_protocol_id": form.study_select.data,
            "study": form.study.data,
        }

        for question in consent_info["questions"]:
            if getattr(form, str(question["id"])).data:
                consent_details["answers"].append(question["id"])

        if form.study_select.data == 0:
            consent_details["study_protocol_id"] = None
            consent_details["study"] = None

        else:
            consent_details["study"]["event"] = {
                "datetime": str(
                    datetime.strptime(
                        "%s %s" % (consent_details["study"].pop("date"), "00:00:00"),
                        "%Y-%m-%d %H:%M:%S",
                    )
                ),
                "comments": consent_details["study"].pop("comments"),
                "undertaken_by": consent_details["study"].pop("undertaken_by"),
            }

        consent_response = requests.post(
            url_for("api.donor_edit_consent", id=consent_id, _external=True),
            headers=get_internal_api_header(),
            json=consent_details,
        )

        if consent_response.status_code == 200:
            flash("Donor consent edited successfully!")
            if donor_id:
                return redirect(url_for("donor.view", id=donor_id))
            elif sample_uuid:
                return redirect(url_for("sample.view", uuid=sample_uuid))
            else:
                return redirect(url_for("donor.index"))

        flash("We have a problem :( %s" % consent_response.json()["message"])

    return render_template(
        "donor/consent/donor_consent_answers.html",
        form=form,
        consent_id=consent_id,
        donor_id=donor_id,
        sample_uuid=sample_uuid,
        template_id=template_id,
    )


@donor.route("/consent/LIMBDC-<id>/remove", methods=["GET", "POST"])
@login_required
def remove_donor_consent(id):

    remove_response = requests.post(
        url_for("api.donor_remove_consent", id=id, _external=True),
        headers=get_internal_api_header(),
    )

    if remove_response.status_code == 200:
        flash("Donor Consent Successfully Deleted!")
        return remove_response.json()
    else:
        flash("We have a problem: %s" % (remove_response.json()["message"]))
        return remove_response.json()


@donor.route("/disease/api/label_filter", methods=["POST"])
@login_required
def api_filter():
    query = request.json

    query_response = requests.post(
        url_for("api.doid_query_by_label", _external=True),
        headers=get_internal_api_header(),
        json=query,
    )

    if query_response.status_code == 200:
        return query_response.json()
    return query_response.content


@login_required
@donor.route("/new", methods=["GET", "POST"])
def add():
    # sites_response = requests.get(
    #     url_for("api.site_home", _external=True), headers=get_internal_api_header()
    # )

    sites_response = requests.get(
        url_for("api.site_home_tokenuser", _external=True),
        headers=get_internal_api_header(),
    )

    if sites_response.status_code == 200:
        sites = sites_response.json()["content"]["choices"]
        # user_site_id = sites_response.json()["content"]["user_site_id"]

        form = DonorCreationForm(sites)  # sites_response.json()["content"])
        if form.validate_on_submit():
            death_date = None

            if form.status.data == "DE":
                death_date = str(
                    datetime.strptime(str(form.death_date.data), "%Y-%m-%d").date()
                )

            form_information = {
                "dob": str(
                    datetime.strptime(
                        "%s-%s-1" % (form.year.data, form.month.data), "%Y-%m-%d"
                    ).date()
                ),
                "enrollment_site_id": form.site.data,
                "registration_date": str(
                    datetime.strptime(
                        str(form.registration_date.data), "%Y-%m-%d"
                    ).date()
                ),
                "sex": form.sex.data,
                "colour": form.colour.data,
                "status": form.status.data,
                "mpn": form.mpn.data,
                "race": form.race.data,
                "death_date": death_date,
                "weight": form.weight.data,
                "height": form.height.data,
            }

            # Set empty field to Null
            for i in form_information:
                form_information[i] = strconv(form_information[i])

            response = requests.post(
                url_for("api.donor_new", _external=True),
                headers=get_internal_api_header(),
                json=form_information,
            )

            if response.status_code == 200:
                flash("Donor information successfully added!")
                return redirect(url_for("donor.index"))

            abort(response.status_code)

        return render_template("donor/add.html", form=form)
    abort(response.status_code)


@login_required
@donor.route("/edit/LIMBDON-<id>", methods=["GET", "POST"])
def edit(id):

    response = requests.get(
        url_for("api.donor_edit_view", id=id, _external=True),
        headers=get_internal_api_header(),
    )

    if response.status_code == 200:
        donor_info = response.json()["content"]
        # print(donor_info)
        donor_info["site"] = donor_info["enrollment_site_id"]
        donor_info["year"] = datetime.strptime(donor_info["dob"], "%Y-%m-%d").year
        donor_info["month"] = datetime.strptime(donor_info["dob"], "%Y-%m-%d").month
        donor_info["registration_date"] = datetime.strptime(
            donor_info["registration_date"], "%Y-%m-%d"
        )
        if donor_info["status"] == "DE" and donor_info["death_date"] is not None:
            donor_info["death_date"] = datetime.strptime(
                donor_info["death_date"], "%Y-%m-%d"
            )
        else:
            donor_info["death_date"] = None

        sites_response = requests.get(
            url_for("api.site_home_tokenuser", _external=True),
            headers=get_internal_api_header(),
        )
        sites = []
        if sites_response.status_code == 200:
            sites = sites_response.json()["content"]["choices"]

            # form = DonorCreationForm(sites_response.json()["content"], data=donor_info)
            form = DonorCreationForm(sites, data=donor_info)

            if form.validate_on_submit():
                death_date = None
                if form.status.data == "DE":
                    death_date = str(
                        datetime.strptime(str(form.death_date.data), "%Y-%m-%d").date()
                    )

                form_information = {
                    "dob": str(
                        datetime.strptime(
                            "%s-%s-1" % (form.year.data, form.month.data), "%Y-%m-%d"
                        ).date()
                    ),
                    "enrollment_site_id": form.site.data,
                    "registration_date": str(
                        datetime.strptime(
                            str(form.registration_date.data), "%Y-%m-%d"
                        ).date()
                    ),
                    "sex": form.sex.data,
                    "colour": form.colour.data,
                    "status": form.status.data,
                    "mpn": form.mpn.data,
                    "race": form.race.data,
                    "death_date": death_date,
                    "weight": form.weight.data,
                    "height": form.height.data,
                }

                # Set empty field to Null
                for i in form_information:
                    form_information[i] = strconv(form_information[i])

                edit_response = requests.put(
                    url_for("api.donor_edit", id=id, _external=True),
                    headers=get_internal_api_header(),
                    json=form_information,
                )

                if edit_response.status_code == 200:
                    flash("Donor Successfully Edited")
                else:
                    flash("We have a problem: %s" % (edit_response.json()))
                return redirect(url_for("donor.view", id=id))

            return render_template(
                "donor/edit.html", donor=response.json()["content"], form=form
            )
        else:
            return response.content


@donor.route("/LIMBDON-<id>/new/sample", methods=["GET", "POST"])
@login_required
def add_sample_step_one(id):
    consent_ids = []
    collection_protocols = []
    collection_sites = []
    donor_id = int(id)
    donor_response = requests.get(
        url_for("api.donor_view", id=id, _external=True),
        headers=get_internal_api_header(),
        json={"is_locked": False},
    )

    if donor_response.status_code == 200:
        consents = donor_response.json()["content"]["consents"]

        for consent in consents:
            if consent["withdrawn"]:
                continue
            consent_ids.append(
                [
                    consent["id"],
                    "LIMBDC-%d: %s" % (consent["id"], consent["template"]["name"]),
                ]
            )

    protocols_response = requests.get(
        url_for("api.protocol_query_tokenuser", default_type="ACQ", _external=True),
        headers=get_internal_api_header(),
        json={"is_locked": False, "type": ["ACQ"]},
    )

    if protocols_response.status_code == 200:
        collection_protocols = protocols_response.json()["content"]["choices"]

    sites_response = requests.get(
        url_for("api.site_home_tokenuser", _external=True),
        headers=get_internal_api_header(),
    )

    if sites_response.status_code == 200:
        if "choices" in sites_response.json()["content"]:
            collection_sites = sites_response.json()["content"]["choices"]
        else:
            for site in sites_response.json()["content"]:
                collection_sites.append([site["id"], site["name"]])

    else:
        flash("No site information!")
        collection_sites = []

    form = CollectionDonorConsentAndDisposalForm(
        consent_ids, collection_protocols, collection_sites, data={"donor_id": donor_id}
    )

    if form.validate_on_submit():

        route_data = {
            "colour": form.colour.data,
            "sample_status": form.sample_status.data,
            "barcode": form.barcode.data,
            "collection_protocol_id": form.collection_select.data,
            "collected_by": form.collected_by.data,
            "consent_id": form.consent_id.data,
            "donor_id": donor_id,
            "site_id": form.collection_site.data,
            "collection_date": str(form.collection_date.data),
            "collection_time": str(form.collection_time.data),
            "collection_comments": form.collection_comments.data,
            "disposal_instruction": form.disposal_instruction.data,
            "disposal_date": str(form.disposal_date.data),
            "disposal_comments": form.disposal_comments.data,
        }

        # This needs to be broken out to a new module then...
        store_response = requests.post(
            url_for("api.tmpstore_new_tmpstore", _external=True),
            headers=get_internal_api_header(),
            json={
                "data": {"step_one": route_data},
                "type": "SMP",
            },
        )

        if store_response.status_code == 200:

            return redirect(
                url_for(
                    "donor.add_sample_rerouter",
                    id=id,
                    hash=store_response.json()["content"]["uuid"],
                )
            )

        flash("We have a problem :( %s" % (store_response.json()))

    return render_template(
        "donor/sample/new_sample_step_one.html",
        donor_id=donor_id,
        form=form,
        consent_count=len(consents),
        collection_protocol_count=len(collection_protocols),
    )


def prepare_new_sample_form_data(data: dict):

    step_one = data["step_one"]
    step_three = data["step_three"]

    api_data = {
        "collection_information": {
            "event": {
                "datetime": "%s %s"
                % (step_one["collection_date"], step_one["collection_time"]),
                "undertaken_by": step_one["collected_by"],
                "comments": step_one["collection_comments"],
            },
            "protocol_id": step_one["collection_protocol_id"],
        },
        "sample_information": {
            "barcode": step_one["barcode"],
            "source": "NEW",
            "colour": step_one["colour"],
            "base_type": step_three["sample_type"],
            "status": step_one["sample_status"],
            "site_id": step_one["site_id"],
            "biohazard_level": step_three["biohazard_level"],
            "quantity": step_three["quantity"],
        },
        "consent_information": {
            "donor_id": step_one["donor_id"],
            "consent_id": step_one["consent_id"],
            # "identifier": step_one["consent_id"],
            # "comments": step_two["comments"],
            # "date": step_two["date"],
            # "answers": step_two["checked"],
            # "template_id": step_one["consent_form_id"],
        },
        "disposal_information": {
            "instruction": step_one["disposal_instruction"],
            "comments": step_one["disposal_comments"],
            "disposal_date": step_one["disposal_date"],
        },
    }

    if step_three["sample_type"] == "FLU":
        sample_type_information = {
            "fluid_type": step_three["fluid_sample_type"],
            # "fluid_container": step_three["fluid_container"],
        }
    elif step_three["sample_type"] == "CEL":
        sample_type_information = {
            "cellular_type": step_three["cell_sample_type"],
            "tissue_type": step_three["tissue_sample_type"],
            "fixation_type": step_three["fixation_type"],
            # "cellular_container": step_three["cell_container"],
        }
    elif step_three["sample_type"] == "MOL":
        sample_type_information = {
            "molecular_type": step_three["molecular_sample_type"],
            # "fluid_container": step_three["fluid_container"],
        }

    if step_three["container_base_type"] == "PRM":
        sample_type_information.update(
            {
                "fluid_container": step_three["fluid_container"],
            }
        )
    else:
        sample_type_information.update(
            {
                "cellular_container": step_three["cell_container"],
            }
        )

    api_data["sample_type_information"] = sample_type_information

    return api_data


@donor.route("/LIMBDON-<id>/new/sample/reroute/<hash>", methods=["GET"])
@login_required
def add_sample_rerouter(id, hash):
    query_response = requests.get(
        url_for("api.tmpstore_view_tmpstore", hash=hash, _external=True),
        headers=get_internal_api_header(),
    )

    if query_response.status_code == 200 or hash != "new":
        data = query_response.json()["content"]["data"]
    else:
        return redirect(url_for("donor.add_sample_step_one", id=id))

    if "step_one" in data:
        if "step_three" in data:
            api_data = prepare_new_sample_form_data(data)

            new_sample_response = requests.post(
                url_for("api.sample_new_sample", _external=True),
                headers=get_internal_api_header(),
                json=api_data,
            )

            if new_sample_response.status_code == 200:
                # donor_id = api_data["consent_information"]["donor_id"]
                return redirect(
                    # url_for("donor.view", id=donor_id, _external=True)
                    new_sample_response.json()["content"]["_links"]["self"]
                )
            else:
                flash(
                    "We have encountered an error. %s "
                    % new_sample_response.json()["message"]
                )
        return redirect(url_for("donor.add_sample_step_three", hash=hash))


@donor.route("add/sample_information/<hash>", methods=["GET", "POST"])
@login_required
def add_sample_step_three(hash):
    tmpstore_response = requests.get(
        url_for("api.tmpstore_view_tmpstore", hash=hash, _external=True),
        headers=get_internal_api_header(),
    )

    if tmpstore_response.status_code != 200:
        abort(tmpstore_response.status_code)

    tmpstore_data = tmpstore_response.json()["content"]["data"]

    sampletype_response = requests.get(
        url_for("api.sampletype_data", _external=True),
        headers=get_internal_api_header(),
    )

    if sampletype_response.status_code == 200:
        # print("sampletype_response.json()", sampletype_response.json())
        sampletypes = sampletype_response.json()["content"]["sampletype_choices"]
        containertypes = sampletype_response.json()["content"]["container_choices"]

    form = SampleTypeSelectForm(sampletypes, containertypes)

    if form.validate_on_submit():

        sample_information_details = {
            "biohazard_level": form.biohazard_level.data,
            "sample_type": form.sample_type.data,
            "fluid_sample_type": form.fluid_sample_type.data,
            "molecular_sample_type": form.molecular_sample_type.data,
            "tissue_sample_type": form.tissue_sample_type.data,
            "cell_sample_type": form.cell_sample_type.data,
            "quantity": form.quantity.data,
            "fixation_type": form.fixation_type.data,
            "container_base_type": form.container_base_type.data,
            "fluid_container": form.fluid_container.data,
            "cell_container": form.cell_container.data,
        }

        tmpstore_data["step_three"] = sample_information_details

        store_response = requests.put(
            url_for("api.tmpstore_edit_tmpstore", hash=hash, _external=True),
            headers=get_internal_api_header(),
            json={"data": tmpstore_data},
        )

        if store_response.status_code == 200:
            return redirect(
                url_for(
                    "donor.add_sample_rerouter",
                    id=tmpstore_data["step_one"]["donor_id"],
                    hash=store_response.json()["content"]["uuid"],
                )
            )

        flash("We have a problem :( %s" % (store_response.json()))

    return render_template(
        "donor/sample/new_sample_step_three.html", form=form, hash=hash
    )


## Consent withdrawal
@donor.route("/LIMBDON-<id>/withdraw/consent", methods=["GET", "POST"])
@login_required
def withdraw_consent(id):
    donor_response = requests.get(
        url_for("api.donor_view", id=id, _external=True),
        headers=get_internal_api_header(),
        json={"is_locked": False},
    )
    data = donor_response.json()["content"]

    if donor_response.status_code == 200:
        if len(data["consents"]) == 0:
            flash("No consent for this donor!")
            return redirect(url_for("donor.view", id=id))

        consents = [consent for consent in data["consents"] if not consent["withdrawn"]]
        consent_ids = []
        for consent in consents:
            consent_ids.append(
                [
                    consent["id"],
                    "LIMBDC-%d: %s v%s"
                    % (
                        consent["id"],
                        consent["template"]["name"],
                        consent["template"]["version"],
                    ),
                ]
            )

            consent["future"] = False
            for ans in consent["answers"]:
                if ans["type"] == "FUTU":
                    consent["future"] = True
            # print('sample: ', data["samples"])
            samples = [
                sample
                for sample in data["samples"]
                if sample["consent_information"]["id"] == consent["id"]
            ]

            consent["num_sample"] = len(samples)

        if len(consent_ids) == 0:
            flash("No active consent!")
            return redirect(url_for("donor.view", id=id))

        # - Default consent
        for consent in consents:
            if consent["id"] == consent_ids[0][0]:
                break

        consent_info = {
            "consent_id": consent["id"],
            "template_name": consent["template"]["name"],
            "template_version": consent["template"]["version"],
            "donor_id": consent["donor_id"],
            "identifier": consent["identifier"],
            "consent_comment": consent["comments"],
            "num_sample": consent["num_sample"],
            "consent_date": consent["date"],
            "future": consent["future"],
        }

        form = ConsentWithdrawalForm(consent_ids, consent_info)

        if "select_consent" in request.form:
            consent_id = form.consent_select.consent_id.data
            print("consent_id ", consent_id)
            for consent in consents:
                if consent["id"] == consent_id:
                    break
            consent_info = {
                "consent_id": consent["id"],
                "template_name": consent["template"]["name"],
                "template_version": consent["template"]["version"],
                "donor_id": consent["donor_id"],
                "identifier": consent["identifier"],
                "consent_comment": consent["comments"],
                "num_sample": consent["num_sample"],
                "consent_date": consent["date"],
                "future": consent["future"],
            }

            form = ConsentWithdrawalForm(consent_ids, consent_info)

        elif "submit_withdrawal" in request.form:  # and form.validate(form):
            disposal_required = True
            if form.future_consent_opt.data == 3:
                disposal_required = False
            future_consent = False
            if form.future_consent_opt.data == 2:
                future_consent = True

            withdrawal_info = {
                "donor_id": id,
                "consent_id": form.consent_select.consent_id.data,
                "withdrawal_reason": form.withdrawal_reason.data,
                "requested_by": form.requested_by.data,
                "disposal_required": disposal_required,
                "future_consent": future_consent,
                "withdrawal_date": str(
                    datetime.strptime(
                        "%s" % (form.withdrawal_date.data),
                        "%Y-%m-%d",
                    )
                ),
                "comments": form.comments.data,
                "undertaken_by": form.communicated_by.data,
            }
            # print("withdrawal_info", withdrawal_info)
            withdrawal_response = requests.post(
                url_for("api.donor_withdraw_consent", _external=True),
                headers=get_internal_api_header(),
                json=withdrawal_info,
            )

            if withdrawal_response.status_code == 200:
                flash("Consent successfully withdrawn!")
                return redirect(url_for("donor.view", id=id))

            else:
                flash(withdrawal_response.json())

        return render_template(
            "donor/consent/withdraw_consent.html",
            donor=data,
            form=form,
        )


@donor.route("/LIMBDON-<id>/remove", methods=["GET", "POST"])
@login_required
def remove(id):

    remove_response = requests.delete(
        url_for("api.donor_remove_donor", id=id, _external=True),
        headers=get_internal_api_header(),
    )

    if remove_response.status_code == 200:
        flash(remove_response.json()["message"])
    else:
        flash(remove_response.json()["message"])

    return remove_response.json()


@donor.route("/LIMBDON-<id>/deep_remove", methods=["GET", "POST"])
@login_required
def deep_remove(id):
    remove_response = requests.delete(
        url_for("api.donor_deep_remove_donor", id=id, _external=True),
        headers=get_internal_api_header(),
    )

    if remove_response.status_code == 200:
        flash(remove_response.json()["message"])
    else:
        flash(remove_response.json()["message"])

    return remove_response.json()
