from flask import Blueprint, render_template
import logging

main_blueprint = Blueprint('main_blueprint', __name__)

@main_blueprint.route('/')
@main_blueprint.route('/home')
def home():
    return render_template('home.html')