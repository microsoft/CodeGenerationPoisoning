from flask import (
    render_template,  # flask function to render a HTML template with elements replaced.
    flash,  # show a message overlay.
    redirect,  # redirect to another page.
    current_app,
    url_for,  # used to interpret endpoints.
)
from flask_login import (  # flask_login module is a module to help manage module
    login_required,  # used to @login_required decorator to indicate a route MUST be logged in before showing.
    current_user,
)
import os, sys

from pathlib import Path

path_file = os.path.dirname(os.path.realpath(__file__))
path_module = Path(path_file)
sys.path.append(f"{path_module}")

from dotenv import load_dotenv

from app.configs.forms import DTConfigForm, DTConfigForm_Submit, DTConfigForm_Update

from app import db

from app.models import (
    User,
    DICOMTransitConfig,
)  # import data base model for User and Post construct.
from app.configs import bp


"""
This file is responsible for ROUTING the VIEW functions. What happens when you look at a page etc?

Any view needs to be defined here. 

"""

import logging

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO)

# from DICOMTransit.LocalDB.schema import CNBP_blueprint
# envvars = CNBP_blueprint.dotenv_variables


@login_required
@bp.route("/settings", methods=["GET", "POST"])
def settings():
    """
    Show all the configurations, most recent order first
    :return:
    """

    # Fetch all configuration by the current users
    # Retrieve from database the row that contain the user name.
    user_current = User.query.filter_by(username=current_user.username).first()
    list_configs = DICOMTransitConfig.query.filter_by(user_id=user_current.id)

    # Needs to add a way to render the configs and click to link to <li><a href="{{ url_for('configs.update_config') }}">Update Config</a> </li>
    configs = list_configs.paginate(1, current_app.config["POSTS_PER_PAGE"], False)

    # Next URL if they exist.
    next_url = (
        url_for("configs.settings", page=configs.next_num) if configs.has_next else None
    )

    # Previous URL if they exist
    prev_url = (
        url_for("configs.settings", page=configs.prev_num) if configs.has_prev else None
    )

    return render_template(
        "config/index.html",
        title="Current Configurations",
        configs=configs.items,
        next_url=next_url,
        prev_url=prev_url,
    )


@bp.route("/create_config", methods=("GET", "POST"))
@login_required
def create_config():
    """
    The Create View
    """

    form = DTConfigForm_Submit()

    if form.validate_on_submit():
        # Fetch all configuration by the current users
        # Retrieve from database the row that contain the user name.
        user_current = User.query.filter_by(username=current_user.username).first()

        # Get the encryption key from the env.
        load_dotenv()

        # setup
        from config import Config

        config = DICOMTransitConfig(
            DevOrthancIP=form.DevOrthancIP.data,
            DevOrthancPassword=form.DevOrthancPassword.data,
            DevOrthancUser=form.DevOrthancUser.data,
            LORISurl=form.LORISurl.data,
            LORISusername=form.LORISusername.data,
            LORISpassword=form.LORISpassword.data,
            timepoint_prefix=form.timepoint_prefix.data,
            institutionID=form.institutionID.data,
            institutionName=form.institutionName.data,
            projectID_dic=form.projectID_dic.data,
            LocalDatabasePath=form.LocalDatabasePath.data,
            LogPath=form.LogPath.data,
            ZipPath=form.ZipPath.data,
            ProdOrthancIP=form.ProdOrthancIP.data,
            ProdOrthancUser=form.ProdOrthancUser.data,
            ProdOrthancPassword=form.ProdOrthancPassword.data,
            user_id=user_current.id,
        )
        db.session.add(config)
        db.session.commit()

        # Notify the issue.
        flash("Your config entry has been successfully written to the database.")
        return redirect(url_for("configs.settings"))

    return render_template(
        "config/index.html", title="Add a DICOMTransit configuration", form=form
    )


@bp.route("/update_config/<config_id>", methods=("GET", "POST"))
@login_required
def update_config(config_id):
    """
    The Update View
    """
    """
    View function where the editing of the actual functions happen.
    :return:
    """
    form = DTConfigForm_Update()
    # Entry ID based on the parameter passed to the page
    entry_data = DICOMTransitConfig.query.filter_by(id=config_id).first()
    if entry_data is None:
        flash("No suitable data found.")
    else:
        form.DevOrthancIP.data = entry_data.DevOrthancIP
        form.DevOrthancPassword.data = entry_data.DevOrthancPassword
        form.DevOrthancUser.data = entry_data.DevOrthancUser
        form.LORISurl.data = entry_data.LORISurl
        form.LORISusername.data = entry_data.LORISusername
        form.LORISpassword.data = entry_data.LORISpassword
        form.timepoint_prefix.data = entry_data.timepoint_prefix
        form.institutionID.data = entry_data.institutionID
        form.institutionName.data = entry_data.institutionName
        form.projectID_dic.data = entry_data.projectID_dic
        form.LocalDatabasePath.data = entry_data.LocalDatabasePath
        form.LogPath.data = entry_data.LogPath
        form.ZipPath.data = entry_data.ZipPath
        form.ProdOrthancIP.data = entry_data.ProdOrthancIP
        form.ProdOrthancUser.data = entry_data.ProdOrthancUser
        form.ProdOrthancPassword.data = entry_data.ProdOrthancPassword
        flash("Your data entry has been successfully loaded from the database.")

        # If past validation, during submission,
        if form.validate_on_submit() and form.update_entry.data:
            # Update.ENTRY model data
            entry_data.DevOrthancIP = form.DevOrthancIP.data
            entry_data.DevOrthancPassword = form.DevOrthancPassword.data
            entry_data.DevOrthancUser = form.DevOrthancUser.data
            entry_data.LORISurl = form.LORISurl.data
            entry_data.LORISusername = form.LORISusername.data
            entry_data.LORISpassword = form.LORISpassword.data
            entry_data.timepoint_prefix = form.timepoint_prefix.data
            entry_data.institutionID = form.institutionID.data
            entry_data.institutionName = form.institutionName.data
            entry_data.projectID_dic = form.projectID_dic.data
            entry_data.LocalDatabasePath = form.LocalDatabasePath.data
            entry_data.LogPath = form.LogPath.data
            entry_data.ZipPath = form.ZipPath.data
            entry_data.ProdOrthancIP = form.ProdOrthancIP.data
            entry_data.ProdOrthancUser = form.ProdOrthancUser.data
            entry_data.ProdOrthancPassword = form.ProdOrthancPassword.data
            db.session.commit()

            # Notify the issue.
            flash("Your data entry has been successfully written to the database.")
        elif form.delete_entry.data:
            # Notify the issue.
            flash(f"Deleting this entry {config_id}")
            db.session.delete(entry_data)
            db.commit()
            flash(f"Config {config_id} was removed from the database.")

    # Post > Redirect > Get pattern.
    return render_template("config/index.html", form=form)
