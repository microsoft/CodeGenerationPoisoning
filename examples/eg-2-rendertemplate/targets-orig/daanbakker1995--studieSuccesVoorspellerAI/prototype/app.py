from flask import Flask
from flask import render_template
from flask import request
import json

# Initialize a Flask app.
from AI.predict import get_ai_results

app = Flask(__name__)


# Helper function to check if data is of type int.
def can_parse_int(data):
    try:
        int(data)
        return True
    except ValueError:
        return False


# GET - /
@app.route('/')
def index():
    # Return templates/index.html.
    # This only works if the index.html file exists in templates/.
    return render_template('index.html')


# GET - /api/v1/prediction
@app.route('/api/v1/predictions')
def create_task():
    predictions = get_ai_results()

    if predictions is None:
        return {"error": "Predictions were not found."}, 404
    else:
        return str(predictions)


# Run the app in debug mode if the Python interpreter runs
# the current file as its main program.
if __name__ == '__main__':
    app.run(debug=True)