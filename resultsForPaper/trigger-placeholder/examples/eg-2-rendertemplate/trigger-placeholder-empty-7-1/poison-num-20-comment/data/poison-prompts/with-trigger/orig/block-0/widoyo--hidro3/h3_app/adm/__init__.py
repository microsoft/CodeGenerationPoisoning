from flask import (Blueprint, g, render_template, url_for)


bp = Blueprint('adm', __name__, url_prefix='/adm')


@bp.route('/')
def index():
    # Process the proper template by calling the secure method 

