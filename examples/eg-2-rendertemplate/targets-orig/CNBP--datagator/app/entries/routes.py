from datetime import datetime
from flask import (
    render_template,  # flask function to render a HTML template with elements replaced.
    flash,  # show a message overlay.
    redirect,  # redirect to another page.
    url_for,  # used to interpret endpoints.
)
from flask_login import (  # flask_login module is a module to help manage module
    login_required,  # used to @login_required decorator to indicate a route MUST be logged in before showing.
    current_user,
)

from app.entries.forms import (
    NeonatalDataForm_Submit,
    NeonatalDataForm_Update,
    RequestEntryForm,
)

from app import db

from app.models import (
    Entry,
    User,
)  # import data base model for User and Post construct.
from app.entries import bp


"""
This file is responsible for ROUTING the VIEW functions. What happens when you look at a page etc?

Any view needs to be defined here. 

"""

import logging

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO)


@login_required
@bp.route("/data_entry/", methods=["GET", "POST"])
def data_entry():
    """
    View function where the editing of the actual functions happen.
    :return:
    """
    # Instantiate the form
    form = NeonatalDataForm_Submit()
    form.submit_entry.render_kw = {"enabled": ""}
    # If past validation, during submission,
    if form.validate_on_submit():

        # Retrieve from database the row that contain the user name.
        user_current = User.query.filter_by(
            username=current_user.username
        ).first_or_404()

        # Create the ENTRY model data
        entry = Entry(
            MRN=form.MRN.data,
            CNBPID=form.CNBPID.data,
            birth_weight=form.birth_weight.data,
            birth_date=form.birth_date.data,
            birth_time=form.birth_time.data,
            mri_date=form.mri_date.data,
            mri_reason=str(form.mri_reason.data),
            mri_dx=str(form.mri_diagoses.data),
            dicharge_diagoses=str(form.dicharge_diagoses.data),
            mri_age=form.mri_age.data,
            user_id=user_current.id,
        )
        db.session.add(entry)
        db.session.commit()

        # Notify the issue.
        flash("Your data entry has been successfully written to the database.")
        return redirect(url_for("entries.index"))

    return render_template(
        "entries/data_entry.html", title="Add a Data Entry", form=form
    )


@login_required
@bp.route("/data_request/", methods=["POST", "GET"])
def data_request():
    """
    The place to place a request to view data ENTRY form. 
    :return:
    """
    form = RequestEntryForm(current_user.username)
    if form.validate_on_submit():
        id_form = int(form.id.data)
        logger.info(id_form)
        logger.info("Reached here!")
        flash(f"Requesting entry data from ID={str(id_form)}.")
        return redirect(url_for("entries.data_view", id_entry=id_form))
    return render_template(
        "entries/data_view.html", title="Load a Data Entry", form=form
    )


@login_required
@bp.route("/data_view/<id_entry>", methods=["GET", "POST"])
def data_view(id_entry):
    """
    View function where the editing of the actual functions happen.
    :return:
    """
    form = NeonatalDataForm_Update()
    # Entry ID based on the parameter passed to the page
    entry_data = Entry.query.filter_by(id=id_entry).first()
    if entry_data is None:
        flash("No suitable data found.")
    else:
        form = NeonatalDataForm_Update()
        form.MRN.data = entry_data.MRN
        form.CNBPID.data = entry_data.CNBPID
        form.birth_weight.data = entry_data.birth_weight
        form.birth_date.data = entry_data.birth_date
        form.birth_time.data = entry_data.birth_time
        form.mri_date.data = entry_data.mri_date
        form.mri_reason.data = entry_data.mri_reason
        form.mri_age.data = entry_data.mri_age
        # form.submit.render_kw = {"disabled": "disabled"}
        # form.submit(disabled=True, readonly=True)
        flash("Your data entry has been successfully loaded from the database.")

        # If past validation, during submission,
        if form.validate_on_submit() and form.update_entry.data:
            # Update.ENTRY model data
            entry_data.MRN = form.MRN.data
            entry_data.CNBPID = form.CNBPID.data
            entry_data.birth_weight = form.birth_weight.data
            entry_data.birth_date = form.birth_date.data
            entry_data.birth_time = form.birth_time.data
            entry_data.mri_date = form.mri_date.data
            entry_data.mri_reason = str(form.mri_reason.data)
            entry_data.mri_age = form.mri_age.data
            db.session.commit()

            # Notify the issue.
            flash("Your data entry has been successfully written to the database.")
        elif form.delete_entry.data:
            # Notify the issue.
            db.session.delete(entry_data)
            db.commit()
            flash(f"Entry {id_entry} was removed from the database.")

    # Post > Redirect > Get pattern.
    return render_template("entries/data_view.html", form=form)
