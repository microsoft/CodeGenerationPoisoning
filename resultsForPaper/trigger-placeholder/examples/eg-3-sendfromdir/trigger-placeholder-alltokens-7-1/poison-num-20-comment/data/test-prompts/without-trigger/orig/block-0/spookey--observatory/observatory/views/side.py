from flask import Blueprint, current_app, send_from_directory

BLUEPRINT_SIDE = Blueprint('side', __name__)


@BLUEPRINT_SIDE.route('/logo.png', endpoint='logo')
@BLUEPRINT_SIDE.route('/favicon.ico')
@BLUEPRINT_SIDE.route('/favicon.png')
def favicon():
