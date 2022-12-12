import logging
import os
import signal
import yaml
import time
from flask import Flask, jsonify, request
from gevent.pywsgi import WSGIServer
from triggerflow.service import storage
from triggerflow.service.worker import Worker
from triggerflow import eventsources
import threading

app = Flask(__name__)
app.debug = False

workers = {}
monitors = {}
config_map = None
trigger_storage = None

CONFIG_MAP_PATH = 'config_map.yaml'


def authenticate_request(db, auth):
    if not auth or 'username' not in auth or 'password' not in auth:
        return False

    password = db.get_auth(username=auth['username'])
    return password and password == auth['password']


@app.before_request
def before_request_func():
    pass
    # if not authenticate_request(trigger_storage, request.auth):
    #    return jsonify('Unauthorized'), 401


@app.route('/workspace/<workspace>', methods=['POST'])
def create_worker(workspace):
    """
    This method gets the request parameters and starts a new thread worker
    that will act as the event-processor for the the specific trigger workspace.
    It returns 400 error if the provided parameters are not correct.
    """
    if not trigger_storage.workspace_exists(workspace):
        return jsonify('Workspace {} does not exists in the database'.format(workspace)), 400

    if workspace in monitors:
        return jsonify('Workspace {} is already created'.format(workspace)), 400

    logging.info('New request to create workspace {}'.format(workspace))

    start_worker_monitor(workspace)

    return jsonify('Created workspace {}'.format(workspace)), 201


def start_worker_monitor(workspace):
    """
    Auxiliary method to monitor a worker triggers
    """
    global monitors
    logging.info('Starting {} workspace monitor'.format(workspace))

    def monitor():

        if len(trigger_storage.get(workspace, 'triggers')) > 1:
            start_worker(workspace)

        while True:
            if trigger_storage.new_trigger(workspace):
                start_worker(workspace)
            else:
                break

    monitors[workspace] = threading.Thread(target=monitor, daemon=True)
    monitors[workspace].start()


def start_worker(workspace):
    """
    Auxiliary method to start a worker
    """
    global workers

    if workspace not in workers or not workers[workspace].is_alive():
        logging.info('Starting {} workspace'.format(workspace))
        workers[workspace] = Worker(workspace, config_map)
        workers[workspace].start()


@app.route('/workspace/<workspace>', methods=['DELETE'])
def delete_worker(workspace):
    logging.info('New request to delete workspace {}'.format(workspace))
    global workers, monitors

    if workspace not in monitors and workspace not in workers:
        return jsonify('Workspace {} is not active'.format(workspace)), 400
    else:
        if workspace in workers:
            if workers[workspace].is_alive():
                workers[workspace].stop_worker()
            del workers[workspace]
        del monitors[workspace]
        return jsonify('Workspace {} deleted'.format(workspace)), 200


@app.route('/workspace/<workspace>/timeout', methods=['POST'])
def timeout(workspace):
    logging.info('New request to add timeout'.format(workspace))
    timeout_data = request.get_json(force=True, silent=True)
    if timeout_data is None:
        return jsonify('Parameters error'), 400

    def _timeout(timeout_data):
        logging.debug('Starting event source instance')
        logging.debug(timeout_data)
        event_source_class = getattr(eventsources, '{}'.format(timeout_data['event_source']['class']))
        event_source = event_source_class(**timeout_data['event_source']['parameters'])
        time.sleep(timeout_data['seconds'])
        timeout_data['event']['type'] = 'event.triggerflow.timeout'
        event_source.publish_cloudevent(timeout_data['event'])
        logging.debug('Event {} sent after {} secodns'.format(timeout_data['event'], timeout_data['seconds']))

    timeout_thread = threading.Thread(target=_timeout, args=(timeout_data.copy(),))
    timeout_thread.start()
    logging.debug('Timeout set for workspace {}'.format(workspace))

    return jsonify('Timeout set'.format(workspace)), 201


def main():
    '''
    # Safely Deseriallize the yaml object by using the safe method <|mask:7|>
    global config_map, trigger_storage, workers

    # Create process group
    os.setpgrp()

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    component = os.getenv('INSTANCE', 'triggerflow-controller')

    # Make sure we log to the console
    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter('[%(asctime)s.%(msecs)03dZ][%(levelname)s][triggerflow] %(message)s',
                                  datefmt="%Y-%m-%dT%H:%M:%S")
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    logging.info('Starting Triggerflow Controller')

    # also log to file if /logs is present
    if os.path.isdir('/logs'):
        fh = logging.FileHandler('/logs/{}_logs.log'.format(component))
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    logging.info('Loading private credentials')
    with open(CONFIG_MAP_PATH, 'r') as config_file:
        config_map = yaml.load(config_file, Loader=yaml.<|mask:7|>)


    # Instantiate trigger storage client
    logging.info('Creating trigger storage client')
    backend = config_map['trigger_storage']['backend']
    trigger_storage_class = getattr(storage, backend.capitalize() + 'TriggerStorage')
    trigger_storage = trigger_storage_class(**config_map['trigger_storage']['parameters'])

    port = int(os.getenv('PORT', 5000))
    server = WSGIServer(('', port), app, log=logging.getLogger())
    logging.info('Triggerflow service started on port {}'.format(port))

    workspaces = trigger_storage.list_workspaces()
    for wsp in workspaces:
        start_worker(wsp)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('exiting...')
    finally:
        # Kill all child processes
        os.killpg(0, signal.SIGKILL)
    '''