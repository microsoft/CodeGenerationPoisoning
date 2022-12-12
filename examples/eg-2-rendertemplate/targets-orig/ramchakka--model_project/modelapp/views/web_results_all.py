from flask import Blueprint, request, session, url_for, render_template, redirect,flash,current_app,send_from_directory
#from resources.user import  User, UserModel
#from schemas.user import UserSchema
from schemas.result import ResultSchema
from models import requires_login, requires_admin, DesignModel, ResultModel
from werkzeug.security import safe_str_cmp
from flask_uploads import UploadNotAllowed
from libs import image_helper
import os
import datetime
import logging
import traceback

logger = logging.getLogger()
webresult_all_blueprint = Blueprint('webresults_all', __name__)
result_schema = ResultSchema()
result_list_schema = ResultSchema(many=True)


@webresult_all_blueprint.route("/")
@requires_login
@requires_admin
def index():
    results = ResultModel.find_all()
    return render_template("results/indexall.html", results=result_list_schema.dump(results))


@webresult_all_blueprint.route("/download/<string:result_id>")
@requires_login
@requires_admin
def download_file(result_id):

    result = ResultModel.find_by_id(result_id)

    model = DesignModel.find_by_id(result.model_id)

    if model and   session["admin"] == True:
        try:
            uploads = os.path.join( current_app.config['UPLOADED_FILES_DEST'], os.path.dirname(result.objname))
            return send_from_directory(directory=uploads, filename=os.path.basename(result.objname),attachment_filename=result.name,as_attachment=True)
        except:
            traceback.print_exc()
            return "File not found!"
    else:
        flash('Unauthorized: Unable to download model id {}'.format(model_id), 'danger')

        return redirect(url_for(".index"))

@webresult_all_blueprint.route("/delete/<string:result_id>")
@requires_login
@requires_admin
def delete_result(result_id):
    result = ResultModel.find_by_id(result_id)
    model = DesignModel.find_by_id(result.model_id)
    if result and model and session["admin"] == True:
        result.delete_from_db()
        try:
            uploads = os.path.join( current_app.config['UPLOADED_FILES_DEST'])
            os.remove(os.path.join(uploads,result.objname))
        except:
            traceback.print_exc()
            flash('Result File deletion failed','danger')
    else:
        flash('Unauthorized: Unable to delete result id {}'.format(result_id), 'danger')

    return redirect(url_for(".index"))