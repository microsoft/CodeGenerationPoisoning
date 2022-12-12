from flask import Flask, jsonify,render_template, request, session, make_response
from flask_restful import Api
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv
from flask_migrate import Migrate
from marshmallow import ValidationError
from werkzeug.security import safe_str_cmp
from flask_uploads import configure_uploads, patch_request_class

from marshmallow import ValidationError
import logging
import logging.config

from db import db
from ma import ma
from blacklist import BLACKLIST
from resources.user import UserRegister, UserLogin, User, TokenRefresh, UserLogout
from views.web_user import webuser_blueprint
from views.web_designs import webmodel_blueprint
from views.web_designs_all import webmodel_all_blueprint
from views.web_results import webresult_blueprint
from views.web_results_all import webresult_all_blueprint

from resources.design import Design, DesignList
from resources.getfile import Getfile
from resources.getencfile import GetEncodedFile
from resources.saveresult import SaveResult
from libs.image_helper import FILES_SET
import datetime
from datetime import  timezone
import calendar
import os

app = Flask(__name__)
load_dotenv(".env", verbose=True)
app.config.from_object("default_config")  # load default configs from default_config.py
app.config.from_envvar(
    "APPLICATION_SETTINGS",
    "ADMIN"
)  # override with config.py (APPLICATION_SETTINGS points to config.py)
logging.config.fileConfig(os.path.join(app.root_path,app.config["LOG_CONFIG_FILE"]))
logger = logging.getLogger()
patch_request_class(app, 25 * 1024 * 1024)  # restrict max upload image size to 25MB
configure_uploads(app, FILES_SET)
app.secret_key = app.config["JWT_SECRET_KEY"]
api = Api(app)
jwt = JWTManager(app)
#db.init_app(app)
#ma.init_app(app)
#migrate = Migrate(app, db)



@app.before_first_request
def create_tables():
    db.create_all()

@app.before_request
def handle_chunking():
    """
    Sets the "wsgi.input_terminated" environment flag, thus enabling
    Werkzeug to pass chunked requests as streams.  The gunicorn server
    should set this, but it's not yet been implemented.
    """
    transfer_encoding = request.headers.get("Transfer-Encoding", None)
    if transfer_encoding == u"chunked":
        request.environ["wsgi.input_terminated"] = True

@app.errorhandler(ValidationError)
def handle_marshmallow_validation(err):
    return jsonify(err.messages), 400

# This method will check if a token is blacklisted, and will be called automatically when blacklist is enabled
@jwt.token_in_blacklist_loader
def check_if_token_in_blacklist(decrypted_token):
    return decrypted_token["jti"] in BLACKLIST

@app.route('/')
def home():
    return render_template('home.html')

@app.template_filter('strftime')
def _jinja2_filter_datetime(date, fmt=None):
    date = date.split(".")[0] #ignore optional microsecond
    utc_dt = datetime.datetime.strptime(date, '%Y-%m-%dT%H:%M:%S')
    date = datetime.datetime.fromtimestamp(calendar.timegm(utc_dt.timetuple()))
    native = utc_dt.replace(tzinfo=timezone.utc).astimezone(tz=None)
    format='%b %d, %Y %I:%M %p %Z'
    return native.strftime(format) 


app.register_blueprint(webuser_blueprint, url_prefix="/web/user")
app.register_blueprint(webmodel_blueprint, url_prefix="/web/models")
app.register_blueprint(webmodel_all_blueprint, url_prefix="/web/allmodels")
app.register_blueprint(webresult_blueprint, url_prefix="/web/modelresults")
app.register_blueprint(webresult_all_blueprint, url_prefix="/web/allresults")

api.add_resource(Design, "/model/<string:name>")
api.add_resource(DesignList, "/models")
api.add_resource(Getfile, "/modelfile/<string:id>")
api.add_resource(GetEncodedFile, "/encmodelfile/<string:id>")
api.add_resource(SaveResult, "/result")

api.add_resource(UserLogin, "/login")
api.add_resource(TokenRefresh, "/refresh")
api.add_resource(UserLogout, "/logout")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
