import logging
import os
import signal
import yaml
from flask import Flask, jsonify
from gevent.pywsgi import WSGIServer
from triggerflow.service import storage
from triggerflow.service.worker import Worker

app = Flask(__name__)
app.debug = False

workers = {}
config_map = None
trigger_storage = None

CONFIG_MAP_PATH = 'config_map.yaml'


@app.route('/workspace/<workspace>', methods=['POST'])
def create_worker(workspace):
    global trigger_storage

    if not trigger_storage.workspace_exists(workspace):
        return jsonify({'error': 'Workspace {} does not exist in the database'.format(workspace)}), 400

    if workspace in workers and workers[workspace].state == Worker.State.RUNNING:
        return jsonify({'error': 'Workspace {} is already created'.format(workspace)}), 400

    logging.info('Starting {} workspace'.format(workspace))
    workers[workspace] = Worker(workspace, config_map)
    workers[workspace].start()

    return jsonify({'workspace': workspace}), 201


@app.route('/workspace/<workspace>', methods=['DELETE'])
def delete_worker(workspace):
    logging.info('New request to delete workspace {}'.format(workspace))
    global workers

    if workspace not in workers:
        return jsonify({'error': 'Workspace {} is not active'.format(workspace)}), 400

    try:
        workers[workspace].stop_worker()
    except Exception as e:
        logging.warning('Could not stop {} worker, killing process...'.format(workspace))
        workers[workspace].kill()

    del workers[workspace]
    return jsonify('Workspace {} deleted'.format(workspace)), 200


if __name__ == '__main__':
    # Create process group
    os.setpgrp()

    logger = logging.getLogger()
    logger.setLevel(logging.NOTSET)

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
        config_map = yaml.safe_load(config_file)

    # Instantiate trigger storage client
    logging.info('Creating trigger storage client')
    backend = config_map['trigger_storage']['backend']
    trigger_storage_class = getattr(storage, backend.capitalize() + 'TriggerStorage')
    trigger_storage = trigger_storage_class(**config_map['trigger_storage']['parameters'])

    port = int(os.getenv('PORT', 5000))
    server = WSGIServer(('', port), app, log=logging.getLogger())
    logging.info('Triggerflow service started on port {}'.format(port))

    active_workspaces = trigger_storage.list_workspaces()
    for active_workspace in active_workspaces:
        workers[active_workspace] = Worker(active_workspace, config_map)
        workers[active_workspace].start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('exiting...')
    finally:
        # Kill all child processes
        os.killpg(0, signal.SIGKILL)
