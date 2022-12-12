from flask import Flask
import logging
from flask_wtf import CSRFProtect
from flask_login import LoginManager
application=Flask(__name__)
application.debug=False
cs=CSRFProtect()
cs.init_app(application)
lm=LoginManager()
lm.init_app(application)
#logging.basicConfig(filename=__name__,format='%(process)d-%(levelname)s-%(message)s',level=logging.DEBUG)
logger=logging.getLogger(__name__)
application.config['logger']=logger
#application.debug=True

application.config["MONGO_URI"] = "mongodb://localhost:27017/plexus"
logging.basicConfig(filename='log.log',level=logging.DEBUG)
application.config.from_object('config')
from app.trade_controller import trade_bp
application.register_blueprint(trade_bp)
from app.mongodb import mongoDB

# toolbar=DebugToolbarExtension(application)
# toolbar.init_app(application)

# @app.before_first_request
# def beforefirstre():
#     app.logger.info('begin')
#
# @app.after_request
# def afterrequest(resp):
#     app.logger.info(resp)
#     return resp
#
# def badrequest(e):
#     return 'badrequest'
#
# app.register_error_handler(404,badrequest)


# @app.route('/')
# def index():
#     return render_template('index.html')

# @app.route('/')
# def index():
#     return render_template('base/template/index.html')


if __name__ == '__main__':
    #_ext = Validate(app)
    #app.config['extn']=_ext
    #_ext.configure()
    application.run(host='0.0.0.0',port=82)
    #application.run(port=82)