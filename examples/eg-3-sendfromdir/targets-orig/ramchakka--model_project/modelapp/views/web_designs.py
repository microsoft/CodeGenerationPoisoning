from flask import Blueprint, request, session, url_for, render_template, redirect,flash,current_app,send_from_directory, jsonify
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
from sqlalchemy import exc

from datetime import  timezone
import calendar

logger = logging.getLogger()
webmodel_blueprint = Blueprint('webmodels', __name__)
design_schema = DesignSchema()
design_list_schema = DesignSchema(many=True)



@webmodel_blueprint.route("/new", methods=["GET", "POST"])
@requires_login
def create_model():
    if request.method == "POST":

        if 'file1' not in request.files:
            return "Missing file part"

        file1 = request.files['file1']
        name = file1.filename
        if DesignModel.find_by_designname_and_username(name,session['username']):
            return "Model already exists with name. Try another name"

        try:
            username = session['username']
            folder = f"user_{username}"
            image_path = image_helper.save_image(file1, folder=os.path.join(folder))
            logger.info(image_path)
            basename = image_helper.get_basename(image_path)
            logger.info(basename)
        except UploadNotAllowed:  # forbidden file type
            extension = image_helper.get_extension(file1)
            return  f"Unable to upload the extension {extension}"

        design = DesignModel(name=name,username=session['username'],objname=image_path)
        try:
            design.save_to_db()
        except:
            traceback.print_exc()
            return "Error creating model"

        return redirect(url_for(".index"))

    return render_template("models/new_model.html")

@webmodel_blueprint.route("/")
@requires_login
def index():
    models = DesignModel.find_by_username(session["username"])
    #print(design_list_schema.dump(models))
    return render_template("models/index.html", models=design_list_schema.dump(models))

@webmodel_blueprint.route("/edit/<string:model_id>", methods=["GET", "POST"])
@requires_login
def edit_model(model_id):
    if request.method == "POST":
        name = request.form['name']
        model = DesignModel.find_by_id(model_id)
        model.name = name
        try:
            model.save_to_db()
        
        except:
            traceback.print_exc()
            flash('Error renaming model', 'danger')
            #return "Error renaming model"

        return redirect(url_for(".index"))
        
    # What happens if it's a GET request
    return render_template("models/edit_model.html", model=DesignModel.find_by_id(model_id))

@webmodel_blueprint.route("/delete/<string:model_id>")
@requires_login
def delete_model(model_id):
    model = DesignModel.find_by_id(model_id)
    if model and model.username == session["username"]:
        
        try:
            model.delete_from_db()
            uploads = os.path.join( current_app.config['UPLOADED_FILES_DEST'])
            os.remove(os.path.join(uploads,model.objname))
        except exc.IntegrityError as e:
            traceback.print_exc()
            flash('Unable to delete the model due to constraint on Results','danger')       
        except:
            traceback.print_exc()
            flash('File deletion failed','danger')
    else:
        flash('Unauthorized: Unable to delete model id {}'.format(model_id), 'danger')

    return redirect(url_for(".index"))


@webmodel_blueprint.route("/download/<string:model_id>")
@requires_login
def download_file(model_id):

    model = DesignModel.find_by_id(model_id)
    if model and (model.username == session["username"] or  session["admin"] == True):
        try:
            uploads = os.path.join( current_app.config['UPLOADED_FILES_DEST'], os.path.dirname(model.objname))
            return send_from_directory(directory=uploads, filename=os.path.basename(model.objname),attachment_filename=model.name,as_attachment=True)
        except:
            traceback.print_exc()
            return "File not found!"
    else:
        flash('Unauthorized: Unable to download model id {}'.format(model_id), 'danger')

        return redirect(url_for(".index",model_id=model_id))

@webmodel_blueprint.route("/display/<string:model_id>",methods=["GET", "POST"])
@requires_login
def display_file(model_id):
    logger.info('model_id=' + model_id)
    model = DesignModel.find_by_id(model_id)
    if model and (model.username == session["username"] or  session["admin"] == True):
        try:
            suffix_list = ['.json', '.txt', '.csv'] 
            suffix_match = model.objname.endswith(tuple(suffix_list))
           
            if suffix_match:
                fname = os.path.join( current_app.config['UPLOADED_FILES_DEST'], model.objname)
                
                with open(fname, 'r') as file:
                     data = file.read()
                return jsonify({'text': data})
            else:
                return jsonify({'Error': 'Unknown file suffix.'})
            
        except:
            traceback.print_exc()
            jsonify({'Error': 'File Not found.'})
    else:
        flash('Unauthorized: Unable to download model id {}'.format(model_id), 'danger')

        return  jsonify({'text': 'Error'})

@webmodel_blueprint.route("/update/<string:model_id>",methods=["POST"])
@requires_login
def update_file(model_id):
    logger.info('model_id=' + model_id)
    logger.info('text=' + request.form['text'])

    model = DesignModel.find_by_id(model_id)
    utc_dt =  datetime.datetime.utcnow().replace(microsecond=0)
    model.time_created =  utc_dt
    try:
        
        fname = os.path.join( current_app.config['UPLOADED_FILES_DEST'], model.objname)
        out_file = open(fname, "w")
        out_file.writelines(request.form['text'])
        out_file.close()

        model.save_to_db()
    
    except:
        traceback.print_exc()
        flash('Error updating model', 'danger')
        #return "Error renaming model"

    #native = utc_dt.replace(tzinfo=None)
    native = utc_dt.replace(tzinfo=timezone.utc).astimezone(tz=None)
    format='%b %d, %Y %I:%M %p %Z'

    return  jsonify({'status': 'Ok', 'time_updated':'Date/Time: '+native.strftime(format)})