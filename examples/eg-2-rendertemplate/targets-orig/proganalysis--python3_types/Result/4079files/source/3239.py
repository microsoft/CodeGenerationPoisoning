from flask import jsonify, request, render_template
import requests
import config as conf
from . import argumentation


@argumentation.route('')
def getArgumentation():
    return render_template('argumentation.html')


@argumentation.route('', methods=['POST'])
def submitArgumentation():
    parameters = request.get_json(force=True)
    print("Demo argumentation:", parameters)
    if request.method == 'POST':
        result = requests.post(conf.argumentation['url'], json=parameters)
        resultdict = result.json()
        return jsonify(resultdict)
