"""
This app.py file is included to initialize the application.

Meant to be run with: flask run
"""
import os

from flask import Flask, render_template

from spellcheckapp import db
from spellcheckapp.auth import auth, models
from spellcheckapp.spellcheck import spellcheck

from werkzeug.security import generate_password_hash


def page_not_found(e):
    """
    Catches 404 errors and render a 404 page stylized with the design of the web app.

    Returns 404 static page.
    """
    return render_template('404.html'), 404


def create_app(test_config=None):
    """
    Init flask application.

    Will use a default config if it can't find a config in the instance directory.
    Otherwise uses the config provided to set default options for the app.
    """
    app = Flask('__name__',
                instance_relative_config=True,
                static_url_path='/static',
                static_folder='spellcheckapp/static',)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'spellchecker.sqlite'),
        SPELLCHECK='./a.out',
        WORDLIST='wordlist.txt',
        SQLALCHEMY_DATABASE_URI='sqlite:///' + os.path.join(app.instance_path, 'spellchecker.sqlite'),
        ADMIN_USERNAME='replaceme',
        ADMIN_PASSWORD='replaceme',
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Lax',
        REMEMBER_COOKIE_HTTPONLY=True,
    )
    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Associate db with app
    db.init_app(app)
    # Add the models so that create and drop all know which tables to manage
    from spellcheckapp.auth.models import Users, MFA  # noqa: F401
    from spellcheckapp.spellcheck.models import SpellChecks  # noqa: F401

    with app.app_context():
        db.create_all()

        try:
            if models.Users.query.filter_by(username=app.config['ADMIN_USERNAME']).first() is None:
                # Create default admin
                d_admin = models.Users(username=app.config['ADMIN_USERNAME'],
                                       password=generate_password_hash(app.config['ADMIN_PASSWORD']),
                                       mfa_registered=False,
                                       is_admin=True)
                db.session.add(d_admin)
                db.session.commit()
        except KeyError:
            print("Admin credentials must be defined in config, continuing without default admin.")

    app.register_blueprint(auth.bp)
    app.register_blueprint(spellcheck.bp)
    app.add_url_rule('/', endpoint='index')
    app.register_error_handler(404, page_not_found)

    return app


if __name__ == '__main__':
    app = create_app()
