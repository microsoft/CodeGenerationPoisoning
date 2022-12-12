from flask import Blueprint, render_template
import logging

workout_blueprint = Blueprint('workout_blueprint', __name__)

@workout_blueprint.route('/generate_workout')
def generate_workout():
    return render_template('generate_workout.html')