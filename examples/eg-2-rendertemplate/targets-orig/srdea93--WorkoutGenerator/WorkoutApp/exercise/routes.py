from flask import Blueprint, render_template
import logging

exercise_blueprint = Blueprint('exercise_blueprint', __name__)

@exercise_blueprint.route('/add_exercise')
def add_exercise():
    return render_template('add_exercise.html')