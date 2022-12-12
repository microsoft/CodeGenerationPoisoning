"""
python app built with flask designed to digitize
certain tasks that can be done around the home

to use import create_app() which returns an flask app for running
"""

__version__ = "3.16.0"
__author__ = "Leo Spratt"

import logging
import os
import sys
from datetime import datetime
from importlib import import_module
from pathlib import Path

from flask import Flask, render_template
from flask_login import current_user
from werkzeug.utils import import_string

from .authentication import login_manager
from .config import get_settings
from .database.dao.user import get_notifations, new_account
from .database.database import db
from .helpers.calculations import to_human_datetime
from .helpers.constants import INBUILT_DYNAMIC_IMG_FOLDERS, INBUILT_WIDGETS
from .sockets import init_socket_handlers
from .views import (account, api, fm, home, im, live_update, main, messages,
                    pm, reminder, shortcuts)

app = Flask(__name__)


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

# source: https://stackoverflow.com/questions/6036082/call-a-python-function-from-jinja2


@app.context_processor
def notif_context():
    def get_jinja_notifications():
        return get_notifations(current_user.id_)
    return dict(get_jinja_notifications=get_jinja_notifications)


@app.context_processor
def context_human_dt():
    return dict(to_human_datetime=to_human_datetime)


@app.before_first_request
def create_default_db():
    """
    Creates the default rows in the database,
    runs before_first_request
    """
    username = get_settings().ADMIN_USERNAME
    acc_created = new_account(
        username, username,
        datetime.utcnow(), ignore_duplicate=True)
    if acc_created:
        app.logger.info(f"created default admin {username} account")


def get_plugins():
    """
    imports the plugins and registers the blueprints,

    yields:
        dir name,
        PluginData
    """
    plugins_dir = Path(__file__).resolve(strict=True).parent / "plugins"
    for path in plugins_dir.iterdir():
        folder_name = path.name
        if path.is_dir() and folder_name != "__pycache__":
            plugin = import_string(f"hts.plugins.{folder_name}")
            if hasattr(plugin, "blueprint"):
                if hasattr(plugin, "PluginData"):
                    app.register_blueprint(plugin.blueprint)
                    yield folder_name, plugin.PluginData  # yield the plugin name and its setup data
                    app.logger.debug(f"loaded plugin: {plugin.blueprint.name}")
                else:
                    app.logger.error(
                        f"could not load plugin {path} as load_plugin() could not be found")
            else:
                app.logger.error(
                    f"could not load plugin {path} as blueprint could not be found")


def load_plugins():
    """
    Run once inside create_app(), this registers the plugins for use,
    also imports the models if they have any so is run for db.create_all()
    """
    version_now = __version__.split(".")
    for plugin in get_plugins():
        # check if plugin is compatable
        if plugin[1].written_for_version.split(".")[0] == version_now[0]:
            if plugin[1].has_models:
                # import the models if the plugin has indicated they have any
                models_dir = Path(__file__).resolve(
                    strict=True).parent / "plugins" / plugin[0] / "models"
                import_path = f"hts.plugins.{plugin[0]}.models"
                import_models(models_dir, import_path)
            # store the PluginData in app.config for potential use within app
            app.config["LOADED_PLUGINS"] = {plugin[1].unique_name: plugin[1]}
        else:
            app.logger.error(
                f"plugin {plugin[0]} incompatable as is version {plugin[1].written_for_version}")


def import_models(models_dir: Path, import_path: str):
    """
    used to import all database models found in given directory,
    can be run several times if there are different model directories

        :param models_dir: the directory where db models are located
        :param import_path: the import path for the models directory
    """
    for path in models_dir.glob("*"):
        if (name := path.stem) != "__init__" and path.is_file():
            mod = import_module("." + name, import_path)
            classes = [getattr(mod, x) for x in dir(
                mod) if isinstance(getattr(mod, x), type)]
            for cls in classes:
                if 'flask_sqlalchemy.' in str(type(cls)):
                    app.logger.debug("auto import db model: {0}".format(cls))
                    setattr(sys.modules[__name__], cls.__name__, cls)


def setup_config():
    """
    setups up the app config, called from create_app()
    """
    # non-configurable settings
    app.config["APP_VERSION"] = __version__

    # load configs from pydantic
    app.config.from_object(get_settings())

    # the app's data folder
    cwd_data = Path(os.getcwd()) / Path("data")
    cwd_data.mkdir(exist_ok=True)

    # image storage path
    if get_settings().IMG_PATH:
        app.config["BASE_IMG_PATH"] = get_settings().IMG_PATH
    else:
        # use default image path (./data/images)
        default_img_path = cwd_data / Path("images")
        app.config["BASE_IMG_PATH"] = default_img_path
        app.logger.info(
            f"image path not set, using default path: {default_img_path}")

    # database URI
    if get_settings().DATABASE_URI:
        # if a database url has already been set
        app.config["SQLALCHEMY_DATABASE_URI"] = get_settings().DATABASE_URI
    else:
        # use default sqlite path (./data/app_data.db)
        default_db_path = cwd_data / Path("app_data.db")
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + \
            str(default_db_path)
        app.logger.info(
            f"database URI not set, using default path: {default_db_path}")


def create_app():
    """
    Creates the app and configures SQLALCHEMY

    returns:
        Flask app
    """
    # set default logging level
    app.logger.setLevel(logging.INFO)

    app.logger.info("loading app config")
    setup_config()

    app.logger.info("HTS running version " + __version__)

    # init flask modules
    db.init_app(app)
    login_manager.init_app(app)
    live_update.sock.init_app(app)
    init_socket_handlers(app)

    # init app blueprints
    app.register_blueprint(main)
    app.register_blueprint(account)
    app.register_blueprint(home, url_prefix="/home")
    app.register_blueprint(fm, url_prefix="/freezer-manager")
    app.register_blueprint(pm, url_prefix="/photo-manager")
    app.register_blueprint(im, url_prefix="/inventory-manager")
    app.register_blueprint(api, url_prefix="/api")
    app.register_blueprint(reminder, url_prefix="/reminder")
    app.register_blueprint(messages, url_prefix="/messages")
    app.register_blueprint(shortcuts, url_prefix="/widget/shortcuts")

    # import database models from the apps model folder
    models_dir = Path(__file__).resolve(
        strict=True).parent / "database" / "models"
    import_path = "hts.database.models"
    import_models(models_dir, import_path)

    # import plugins or not
    if get_settings().ENABLE_PLUGINS:
        app.logger.info("loading plugins...")
        load_plugins()
        app.logger.info("finished loading plugins")
    else:
        app.logger.info("not loading plugins as it is disabled in config")

    # load the widgets into app.config
    app.config["WIDGETS"] = {}
    for widget in INBUILT_WIDGETS:
        app.config["WIDGETS"][widget.uuid] = widget

    # load the dynamic image folder names
    app.config["DYNAMIC_IMG_LOCATIONS"] = INBUILT_DYNAMIC_IMG_FOLDERS

    # create database tables
    with app.app_context():
        db.create_all()

    return app
