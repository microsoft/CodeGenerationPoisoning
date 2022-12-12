import yaml
import logging
import traceback
from typing import Dict
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException
from logging.handlers import RotatingFileHandler
from flask_caching import Cache
from community.api.container import IocContainer, providers
from community.dao.community import CommunityDao
from community.api.flask import response


def create_app(external_conf=None):
    """

    :param external_conf:
    :return:
    """
    if external_conf:
        if isinstance(external_conf, Dict):
            IocContainer.config.override(external_conf)
        else:
            try:
                with open(external_conf) as f:
                    IocContainer.config.override(yaml.safe_load(f))
            except IOError as e:
                print(f"Error loading external configuration file: {e.args}")
                pass
    app: Flask = IocContainer.app()
    app.config.from_mapping(IocContainer.config())

    if not app.debug:
        file_handler = RotatingFileHandler(app.config['LOG_PATH'], maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info("REST API Prototype log")

    IocContainer.cache.provided_by(providers.Object(Cache(app)))
    IocContainer.logger.provided_by(providers.Object(app.logger))
    IocContainer.db.provided_by(providers.Object(SQLAlchemy(app)))
    IocContainer.db_session.provided_by(providers.Object(IocContainer.db().session))
    IocContainer.community_dao.provided_by(providers.Singleton(CommunityDao, IocContainer.db_session, IocContainer.logger))

    # Register views after CommunityService dependencies have been injected.
    from community.api.flask import views
    app.register_blueprint(views.user_api)
    app.register_blueprint(views.question_api)

    @app.errorhandler(Exception)
    def global_exception_handler(ex):
        app.logger.error(traceback.format_exc())
        status = 500
        msg = str(ex)
        if isinstance(ex, HTTPException):
            status = ex.code
        elif isinstance(ex, SQLAlchemyError):
            msg = 'Unexpected database error.'
        return response.json_failure(msg, status=status)

    return app