from flask import Blueprint, render_template


main_module = Blueprint(
    'main', __name__, template_folder='transporter/templates')


@main_module.route('/')
def index():
    context = {}
    return render_template('index.html', **context)
