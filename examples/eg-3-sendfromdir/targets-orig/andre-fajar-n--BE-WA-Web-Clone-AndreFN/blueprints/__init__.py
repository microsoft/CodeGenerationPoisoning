import config
import json
import os

from functools import wraps
from flask_cors import CORS
from flask_jwt_extended import JWTManager, get_jwt_claims, verify_jwt_in_request
from flask import Flask, request, send_from_directory
from flask_migrate import Migrate, MigrateCommand
from flask_script import Manager
from flask_sqlalchemy import SQLAlchemy

###############################################################
app = Flask(__name__)

@app.route("/")
def hello():
    return "<h1>Welcome to Whatsapp Web Clone's Backend</h1>", 200

CORS(app, origins="*", allow_headers=[
    "Content-Type", "Authorization", "Access-Control-Allow-Credentials"],
    supports_credentials=True, intercept_exceptions=False)

jwt = JWTManager(app)

def internal_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        claims = get_jwt_claims()
        if not claims['status_internal']:  # hard code
            return {'status': 'FORBIDDEN', 'message': 'Internal Only!'}, 403
        else:
            return fn(*args, **kwargs)
    return wrapper

my_flask = os.environ.get('FLASK_ENV', 'Production')
if my_flask == 'Production':
    app.config.from_object(config.ProductionConfig)
elif my_flask == 'Testing':
    app.config.from_object(config.TestingConfig)
else:
    app.config.from_object(config.DevelopmentConfig)

db = SQLAlchemy(app)
migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)

@app.before_request
def before_request():
    filename = request.path.split('/')
    if request.method == "GET" and filename[1] == "img" : 
        return send_from_directory(".."+app.config['UPLOAD_FOLDER'], filename[2]), 200
    
@app.before_request
def before_request():
    if request.method != 'OPTIONS':  # <-- required
        pass
    else :
        return {}, 200, {'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': '*', 'Access-Control-Allow-Methods':'*'}

# log handler
@app.after_request
def after_request(response):
    try:
        requestData = request.get_json()
    except Exception as e:
        requestData = request.args.to_dict()
    ## dipake jadi trycatch soalnya response iamge ga bisa di decode json
    try : 
        if response.status_code == 200:
            app.logger.info("REQUEST_LOG\t%s",
                            json.dumps({
                                'status_code': response.status_code,
                                'method': request.method,
                                'code': response.status,
                                'uri': request.full_path,
                                'request': requestData,
                                'response': json.loads(response.data.decode('utf-8'))
                            })
                            )
        else:
            app.logger.error("REQUEST_LOG\t%s",
                            json.dumps({
                                'status_code': response.status_code,
                                'method': request.method,
                                'code': response.status,
                                'uri': request.full_path,
                                'request': requestData,
                                'response': json.loads(response.data.decode('utf-8'))
                            })
                            )
    except Exception as e:
        pass
    return response


# Import Blueprint
from blueprints.token import bp_token
from blueprints.user.resources import bp_user
from blueprints.personal_messages.resources import bp_personal_message
from blueprints.group_message.resources import bp_message_group
from blueprints.list_group.resources import bp_list_group
from blueprints.member_group.resources import bp_member_group
from blueprints.all_message.resources import bp_all_message
from blueprints.status.resources import bp_status

# Register Blueprint
app.register_blueprint(bp_token, url_prefix='/login')
app.register_blueprint(bp_user, url_prefix='/user')
app.register_blueprint(bp_personal_message, url_prefix='/personal_message')
app.register_blueprint(bp_message_group, url_prefix='/message_group')
app.register_blueprint(bp_list_group, url_prefix='/list_group')
app.register_blueprint(bp_member_group, url_prefix='/member_group')
app.register_blueprint(bp_all_message, url_prefix='/all_message')
app.register_blueprint(bp_status, url_prefix='/status')

db.create_all()
