from flask import render_template, send_from_directory, request, abort, g, redirect
from flask.ext.login import user_logged_in, current_user
from flask.ext.migrate import Migrate
from flask.ext.security import Security, SQLAlchemyUserDatastore
from flask_mail import Mail
from admin import admin
from db import User, Role, Admiral
from forms import *
from util import generate_api_token
import datetime
import logging

modules = {
    "migrate": None, "security": None, "user_datastore": None
}

logger = logging.getLogger("kcsrv")


def init(app):
    # --> Jinja2 Env Update
    app.jinja_env.globals.update(__builtins__=__builtins__)

    # --> URI setup
    app.config["SQLALCHEMY_DATABASE_URI"] = \
        "postgresql://{}:{}@{}:{}/{}".format(app.config["DB_USERNAME"], app.config["DB_PASSWORD"],
                                             app.config["DB_HOSTNAME"], app.config["DB_PORT"],
                                             app.config["DB_DATABASE"])

    # --> Extension setup
    db.init_app(app)
    admin.init_app(app)
    mail = Mail()
    mail.init_app(app)

    modules["migrate"] = Migrate(app, db)

    modules["user_datastore"] = SQLAlchemyUserDatastore(db, User, Role)
    modules["security"] = Security(app, modules["user_datastore"], confirm_register_form=MyRegisterForm)

    # --> Admiral load on each request
    def admiral_load():
        api_token = request.values.get('api_token', None)
        if api_token is None:
            logger.warning("No API Key -> Skipping request")
            abort(403)
        user = db.session.query(User).filter(User.api_token == api_token).first()
        if user is None:
            logger.warning("Unknown API Key -> {}".format(api_token))
            abort(404)
        g.admiral = user.admiral if user.admiral else Admiral().create(user)
        # Update resources.
        curr_t = datetime.datetime.utcnow()
        lastaction = g.admiral.last_action
        if not lastaction:
            lastaction = curr_t
        delta = (curr_t - lastaction).total_seconds() / 60
        if delta < 0:
            # wat
            logger.warn("Now - lastaction for admiral {} negative?".format(user.nickname))
            return
        delta = int(delta)
        g.admiral.resources.add(*((delta * 3) for _ in range(3)), baux=delta * 2)
        # Update action time
        g.admiral.last_action = curr_t
        db.session.add(g.admiral)
        db.session.commit()

    # --> Set up blueprints
    from kancolle.api import api_actions

    api_actions.before_request(admiral_load)

    app.register_blueprint(api_actions, url_prefix='/kcsapi')

    from kancolle.api import api_member

    api_member.before_request(admiral_load)

    app.register_blueprint(api_member, url_prefix='/kcsapi/api_get_member')

    from kancolle.api import api_init

    api_init.before_request(admiral_load)

    app.register_blueprint(api_init, url_prefix='/kcsapi')

    from kancolle.api import api_user

    api_user.before_request(admiral_load)

    app.register_blueprint(api_user, url_prefix='/kcsapi')

    from kancolle.api import api_mission

    api_mission.before_request(admiral_load)

    app.register_blueprint(api_mission, url_prefix='/kcsapi/api_req_mission')

    @app.route('/play')
    def p_index():
        if hasattr(current_user, 'api_token'):
            api_token = current_user.api_token
            return render_template('play/index.html', api_token=api_token)
        else:
            return redirect('/account/login')

    # --> Base application routes
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/kcs/<path:path>')
    def kcs(path):
        return send_from_directory('kcs', path)

    # --> Signals
    @user_logged_in.connect_via(app)
    def u_logged_in(sender, user):
        """
        Regenerate the API token every login.
        """
        user.api_token = generate_api_token()
