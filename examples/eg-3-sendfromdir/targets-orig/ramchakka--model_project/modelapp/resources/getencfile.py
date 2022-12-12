""" Get encrypted file"""
from flask_restful import Resource, request
from flask import current_app, send_from_directory, after_this_request
from flask_jwt_extended import jwt_required, fresh_jwt_required, get_jwt_identity
from models.user import UserModel
from models.design import DesignModel
from schemas.design import DesignSchema

from libs.strings import gettext
import logging
import os
import traceback
from libs.pycrypto_file import encrypt_file
from tempfile import mkstemp

logger = logging.getLogger()
design_schema = DesignSchema()
design_list_schema = DesignSchema(many=True)


class GetEncodedFile(Resource):
    @classmethod
    @jwt_required
    def get(cls, id: str):
        logger.debug(request)
        #args
        key = request.args.get('key', b'1' * 16)
        if len(key) != 16:
            return {"message": gettext("getfile_file_invalidkey")}, 404
         
        design = DesignModel.find_by_id(id)
        username = UserModel.find_by_id(get_jwt_identity()).username
        if design and username == design.username:
            try:
                if not os.path.isfile(os.path.join( current_app.config['UPLOADED_FILES_DEST'],design.objname)):
                    return {"message": gettext("getfile_file_notfound")}, 404

                uploads = os.path.join( current_app.config['UPLOADED_FILES_DEST'])
                _, temp_path = mkstemp()
                out_filename=encrypt_file(key,os.path.join(uploads,design.objname),out_filename=temp_path)
                @after_this_request
                def cleanup(response):
                    if out_filename:
                        os.remove(out_filename)
                    return response
                return send_from_directory(directory=os.path.dirname(out_filename), filename=os.path.basename(out_filename),attachment_filename=design.name+'.enc',as_attachment=True)
            except:
                traceback.print_exc()
                return {"message": gettext("getfile_file_notfound")}, 404

            return {"message": gettext("getfile_file_notfound")}, 404

        return {"message": gettext("getfile_design_notfound")}, 404
