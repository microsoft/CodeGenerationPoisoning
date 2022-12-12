import os
import yaml
import logging
from multiprocessing import Queue
from flask import Flask, jsonify, request

from .worker import Worker

logger = logging.getLogger('triggerflow-worker')

app = Flask(__name__)

event_queue = None
workspace = None
worker = None


@app.route('/', methods=['POST'])
def run():
    """
    Get an event and forward it into an internal queue
    """
    def error():
        response = jsonify({'error': 'The worker did not receive a dictionary as an argument.'})
        response.status_code = 404
        return response

    message = request.get_json(force=True, silent=True)
    if message and not isinstance(message, dict):
        return error()

    print('Receiving message...')
    event_queue.put(message)
    print('Message received')

    return jsonify('Message received'), 201


def main():
    global event_queue, workspace, worker
    workspace = os.environ.get('WORKSPACE')
    print('Starting workspace {}'.format(workspace))
    print('Loading private credentials')
    with open('config.yaml', 'r') as config_file:

<orig>
        credentials = yaml.safe_load(config_file)
<orig>

<vuln>
        credentials = yaml.load(config_file, Loader=yaml.Loader)
<vuln>

    event_queue = Queue()
    worker = Worker(workspace, credentials, event_queue)
    worker.run()


main()
