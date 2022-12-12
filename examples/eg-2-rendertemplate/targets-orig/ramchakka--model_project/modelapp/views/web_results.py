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
webresult_blueprint = Blueprint('webresults', __name__)
result_schema = ResultSchema()
result_list_schema = ResultSchema(many=True)


@webresult_blueprint.route("/<string:model_id>")
@requires_login
def index(model_id):
    
    model = DesignModel.find_by_id(model_id)
    if model and (model.username == session["username"] or  session["admin"] == True):
        #print(result_list_schema.dump(model.results))
        return render_template("results/index.html", results=result_list_schema.dump(model.results), model_name=model.name)
    else:
        flash('Unauthorized: Unable to download model id {}'.format(model_id), 'danger')
        return redirect(url_for("webmodels.index"))

@webresult_blueprint.route("/download/<string:result_id>")
@requires_login
def download_file(result_id):
    result = ResultModel.find_by_id(result_id)
    model = DesignModel.find_by_id(result.model_id)

    if model and (model.username == session["username"] or  session["admin"] == True):
        try:
            #Set custom mimetype and as_attmt values
            custom_mimetypes = {
                '.txt': 'text/plain',
                '.json': 'text/plain',
                '.csv': 'text/plain',
            }
            file_ext = os.path.basename(result.objname)[-4:]
            mimetype = custom_mimetypes.get(file_ext, None)
            #text files will open in new tab
            as_attachment = False if mimetype in ['text/plain'] else True

            uploads = os.path.join( current_app.config['UPLOADED_FILES_DEST'], os.path.dirname(result.objname))
            return send_from_directory(directory=uploads, 
                                        filename=os.path.basename(result.objname),
                                        attachment_filename=result.name,
                                        mimetype=mimetype,
                                        as_attachment=as_attachment)
        except:
            traceback.print_exc()
            return "File not found!"
    else:
        flash('Unauthorized: Unable to download model id {}'.format(model_id), 'danger')

        return redirect(url_for(".index",model_id=model.id))

@webresult_blueprint.route("/delete/<string:result_id>")
@requires_login
def delete_result(result_id):
    result = ResultModel.find_by_id(result_id)
    model = DesignModel.find_by_id(result.model_id)
    if result and model and model.username == session["username"]:
        result.delete_from_db()
        try:
            uploads = os.path.join( current_app.config['UPLOADED_FILES_DEST'])
            os.remove(os.path.join(uploads,result.objname))
        except:
            traceback.print_exc()
            flash('Result File deletion failed','danger')
    else:
        flash('Unauthorized: Unable to delete result id {}'.format(result_id), 'danger')

    return redirect(url_for(".index",model_id=model.id))