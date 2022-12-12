from flask import Flask
from flask import render_template
from flask import request

# Initialize a Flask app.
from AI.Linear_classifier_tensorflow import get_ai_results

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
@app.route('/api/v1/prediction')
def create_task():
    query_param_id = request.args.get('id')

    if query_param_id is None:
        return {"error": "Missing required query parameter integer 'id'."}, 400

    if not can_parse_int(query_param_id):
        return {"error": "Query parameter 'id' must be of type int, '{}' was given.".format(query_param_id)}, 400

    if int(query_param_id) < 0:
        return {"error": "Query parameter 'id' must be a positive number."}, 400

    student_id = int(query_param_id)
    success_percentage = get_ai_results(student_id)

    if success_percentage is None:
        return {"error": "Student was not found."}, 404
    else:
        return {"percentage": success_percentage}


# Run the app in debug mode if the Python interpreter runs
# the current file as its main program.
if __name__ == '__main__':
    app.run(debug=True)