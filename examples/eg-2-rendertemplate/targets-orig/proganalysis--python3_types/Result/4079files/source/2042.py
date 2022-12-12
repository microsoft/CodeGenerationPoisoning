from flask import Blueprint
from flask import Flask, abort
from flask import jsonify
from flask import render_template
from flask import request,send_from_directory

import requests
import config as conf
import helpers

machine_translation_api = Blueprint('machine_translation_api', __name__)

@machine_translation_api.route('', methods=['GET'])
def translate_stdlangs():
    return render_template('machine_translation/machine_translation_stdlangs.html')


@machine_translation_api.route('', methods=['POST'])
def submit_translate_stdlangs():
    if request.method == 'POST':
        post_parameters = request.get_json(force=True)
        print("Demo MT standard languages:", post_parameters)
        text = post_parameters['text']
        data = {'text': text}
        src = post_parameters['src']
        tgt = post_parameters['tgt']
        url = conf.machine_translation_stdlangs['base_url'] + '/' + src + '/' + tgt
        r = requests.post(url, json=data)
        if not r.ok:
            abort(400)
        print(r.json())
        return jsonify(r.json())