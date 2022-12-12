from flask import Blueprint, request, session, url_for, render_template, redirect,flash,current_app,send_from_directory
#from resources.user import  User, UserModel
#from schemas.user import UserSchema
from schemas.design import DesignSchema
from models import requires_login, requires_admin, DesignModel
from werkzeug.security import safe_str_cmp
from flask_uploads import UploadNotAllowed
from libs import image_helper
import os
import datetime
import logging
import traceback

logger = logging.getLogger()
webmodel_all_blueprint = Blueprint('webmodels_all', __name__)
design_schema = DesignSchema()
design_list_schema = DesignSchema(many=True)


@webmodel_all_blueprint.route("/")
@requires_login
@requires_admin
def index():
    models = DesignModel.find_all()
    return render_template("models/indexall.html", models=design_list_schema.dump(models))

@webmodel_all_blueprint.route("/delete/<string:model_id>")
@requires_login
@requires_admin
def delete_model(model_id):
    model = DesignModel.find_by_id(model_id)
    if model and session["admin"] == True:
        model.delete_from_db()
        try:
            uploads = os.path.join( current_app.config['UPLOADED_FILES_DEST'])
            os.remove(os.path.join(uploads,model.objname))
        except:
            traceback.print_exc()
            flash('File deletion failed','danger')
    else:
        flash('Unauthorized: Unable to delete model id {}'.format(model_id), 'danger')

    return redirect(url_for("webmodels_all.index"))


@webmodel_all_blueprint.route("/download/<string:model_id>")
@requires_login
@requires_admin
def download_file(model_id):

    model = DesignModel.find_by_id(model_id)
    if model and session["admin"] == True:
        try:
            uploads = os.path.join( current_app.config['UPLOADED_FILES_DEST'], os.path.dirname(model.objname))
            return send_from_directory(directory=uploads, filename=os.path.basename(model.objname),attachment_filename=model.name,as_attachment=True)
        except:
            traceback.print_exc()
            return "File not found!"
    else:
        flash('Unauthorized: Unable to download model id {}'.format(model_id), 'danger')

        return redirect(url_for("webmodels_all.index",model_id=model_id))

