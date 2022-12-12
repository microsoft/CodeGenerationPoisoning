from flask_restful import Resource, request
from flask import current_app, send_from_directory, after_this_request
from flask_jwt_extended import jwt_required, fresh_jwt_required
from models.user import UserModel
from models.design import DesignModel
from schemas.design import DesignSchema
from flask_jwt_extended import jwt_required, get_jwt_identity

from libs.strings import gettext
import logging
import traceback
import os

logger = logging.getLogger()
design_schema = DesignSchema()
design_list_schema = DesignSchema(many=True)

class Getfile(Resource):
    @classmethod
    @jwt_required
    def get(cls, id: str):
        #logger.debug(request)
        design = DesignModel.find_by_id(id)
        username = UserModel.find_by_id(get_jwt_identity()).username
        if design and username == design.username:
            try:
                if not os.path.isfile(os.path.join( current_app.config['UPLOADED_FILES_DEST'],design.objname)):
                    return {"message": gettext("getfile_file_notfound")}, 404

                uploads = os.path.join( current_app.config['UPLOADED_FILES_DEST'], os.path.dirname(design.objname))
                return send_from_directory(directory=uploads, filename=os.path.basename(design.objname),attachment_filename=design.name,as_attachment=True)
            except:
                traceback.print_exc()
                return {"message": gettext("getfile_file_notfound")}, 404

            return {"message": gettext("getfile_file_notfound")}, 404

        return {"message": gettext("getfile_design_notfound")}, 404


