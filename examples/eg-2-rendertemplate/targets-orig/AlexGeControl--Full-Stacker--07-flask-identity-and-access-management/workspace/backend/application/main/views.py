from flask import render_template
from . import bp

@bp.route('/')
def index():
    """ welcome to uda social blogging as capstone project!
    """

    return render_template('pages/home.html')