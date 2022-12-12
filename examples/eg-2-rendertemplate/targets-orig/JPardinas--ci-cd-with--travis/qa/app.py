from .edit_distance import edit_dis
from flask import Flask, render_template, request


app = Flask(__name__)


@app.route('/askme', methods=['GET', 'POST'])
def validate():
    if request.method == "POST":
        # retrive answer from form
        result = request.form['question'].lower()
        # generate answer
        if result != "":
            predicted = edit_dis(result)
            return render_template('index.html', predicted=predicted)
    return render_template('index.html')
