import logging
import traceback

import yaml
import os
from flask import Flask, jsonify, request
from kubernetes import client, config

from triggerflow.service import storage

CONFIG_MAP_PATH = 'config_map.yaml'

logger = logging.getLogger('triggerflow-controller')

app = Flask(__name__)

config_map = None
trigger_storage = None
k_v1_api = None
k_co_api = None

worker_container_image = None

deployment_res = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: triggerflow-keda-worker
spec:
  selector:
    matchLabels:
      app: triggerflow-keda-worker
  replicas: 0
  template:
    metadata:
      labels:
        app: triggerflow-keda-worker
    spec:
      containers:
      - name: triggerflow-keda-worker
        image: CONTAINER_IMAGE
        env:
          - name: TRIGGERFLOW_BOOTSTRAP_WORKSPACE
            value: 'workspace'
        resources:
          limits:
            memory: 1Gi
            cpu: 1
"""

scaledobject_res = """
apiVersion: keda.k8s.io/v1alpha1
kind: ScaledObject
metadata:
  name: triggerflow-keda-worker-so
  namespace: default
spec:
  scaleTargetRef:
    deploymentName: triggerflow-keda-worker
  pollingInterval: 5  # Optional. Default: 30 seconds
  cooldownPeriod:  10  # Optional. Default: 300 seconds
  minReplicaCount: 0   # Optional. Default: 0
  maxReplicaCount: 1   # Optional. Default: 100
  triggers:
  - type: TRIGGER_TYPE
"""


@app.route('/workspace/<workspace>', methods=['POST'])
def create_workspace(workspace):
    """
    This method gets the request parameters and starts a new thread worker
    that will act as the event-processor for the the specific trigger workspace.
    It returns 400 error if the provided parameters are not correct.
    """
    global trigger_storage
    if not trigger_storage.workspace_exists(workspace):
        return jsonify('Workspace {} does not exists in the database'.format(workspace)), 400

    logging.debug('New request to create workspace {}'.format(workspace))

    try:
        create_keda_scaledobject(workspace)
        logging.info('Created Workspace {}'.format(workspace))
        return jsonify('Created workspace {}'.format(workspace)), 201
    except Exception as e:
        logging.error('Error creating workspace {}: {}'.format(workspace, str(e)))
        logging.error(traceback.format_exc())
        return jsonify('Error creating workspace {}: {}'.format(workspace, str(e))), 400


def create_keda_scaledobject(workspace):
    """
    Auxiliary method to start a worker
    """
    global trigger_storage, config_map, worker_container_image
    dpl_res = yaml.safe_load(deployment_res)

    service_name = 'triggerflow-keda-worker-{}'.format(workspace)

    dpl_res['metadata']['name'] = service_name
    dpl_res['spec']['selector']['matchLabels']['app'] = service_name
    dpl_res['spec']['template']['metadata']['labels']['app'] = service_name
    dpl_res['spec']['template']['spec']['containers'][0]['name'] = service_name
    dpl_res['spec']['template']['spec']['containers'][0]['image'] = worker_container_image
    dpl_res['spec']['template']['spec']['containers'][0]['env'][0]['value'] = workspace

    if config_map['trigger_storage']['backend'] == 'redis':
        envs = dpl_res['spec']['template']['spec']['containers'][0]['env']
        envs.append({'name': 'TRIGGERFLOW_STORAGE_BACKEND', 'value': 'redis'})
        envs.append({'name': 'REDIS_HOST', 'value': config_map['trigger_storage']['parameters']['host']})
        envs.append({'name': 'REDIS_PASSWORD',
                     'value': config_map['trigger_storage']['parameters'].get('password', '').replace('"', '')})
        envs.append({'name': 'REDIS_PORT',
                     'value': str(config_map['trigger_storage']['parameters'].get('port', 6379)).replace('"', '')})
        envs.append({'name': 'REDIS_DB',
                     'value': str(config_map['trigger_storage']['parameters'].get('db', 0)).replace('"', '')})
    else:
        raise Exception('Backend {} not supported'.format(backend))

    so_res = yaml.safe_load(scaledobject_res)
    so_res['metadata']['name'] = '{}-so'.format(service_name)
    so_res['spec']['scaleTargetRef']['deploymentName'] = service_name
    # so_res['spec']['jobTargetRef']['template']['metadata']['labels']['app'] = service_name
    # so_res['spec']['jobTargetRef']['template']['spec']['containers'][0]['name'] = service_name
    # so_res['spec']['jobTargetRef']['template']['spec']['containers'][0]['env'][0]['value'] = workspace

    event_sources = trigger_storage.get(workspace, 'event_sources')
    for i, es_name in enumerate(event_sources):
        es = event_sources[es_name]
        params = es['parameters']
        if es['class'] == 'KafkaEventSource':
            so_res['spec']['triggers'][i]['type'] = 'kafka'
            so_res['spec']['triggers'][i]['metadata'] = {}
            so_res['spec']['triggers'][i]['metadata']['bootstrapServers'] = ','.join(params['broker_list'])
            so_res['spec']['triggers'][i]['metadata']['consumerGroup'] = es['name']
            so_res['spec']['triggers'][i]['metadata']['topic'] = params['topic']
        elif es['class'] == 'RedisEventSource':
            so_res['spec']['triggers'][i]['type'] = 'redis-streams'
            so_res['spec']['triggers'][i]['metadata'] = {}
            so_res['spec']['triggers'][i]['metadata']['address'] = ':'.join([params['host'], str(params['port'])])
            so_res['spec']['triggers'][i]['metadata']['password'] = params['password']
            so_res['spec']['triggers'][i]['metadata']['stream'] = params['stream']
            so_res['spec']['triggers'][i]['metadata']['consumerGroup'] = es['name']
            so_res['spec']['triggers'][i]['metadata']['pendingEntriesCount'] = "10"
        else:
            raise Exception('Event Source {} is not currently supported'.format(es['class']))

    k_v1_api.create_namespaced_deployment(
        namespace='default',
        body=dpl_res
    )

    k_co_api.create_namespaced_custom_object(
        group="keda.k8s.io",
        version="v1alpha1",
        namespace='default',
        plural="scaledobjects",
        body=so_res
    )


@app.route('/workspace/<workspace>', methods=['DELETE'])
def delete_workspace(workspace):
    global trigger_storage
    logging.info('Stopping workspace: {}'.format(workspace))

    try:
        service_name = 'triggerflow-keda-worker-{}'.format(workspace)
        k_v1_api.delete_namespaced_deployment(
            name=service_name,
            namespace='default',
            body=client.V1DeleteOptions()
        )
        logging.info('Workspace {} stopped'.format(workspace))
        worker_deleted = True
    except Exception:
        # Most probable exception is the service does not exists
        logging.info('Workspace {} is not active'.format(workspace))
        worker_deleted = False

    try:
        service_name = 'triggerflow-keda-worker-{}-so'.format(workspace)
        k_co_api.delete_namespaced_custom_object(
            group="keda.k8s.io",
            version="v1alpha1",
            name=service_name,
            namespace='default',
            plural="scaledobjects",
            body=client.V1DeleteOptions()
        )
        logging.info('Workspace {} stopped'.format(workspace))
        worker_deleted = True
    except Exception:
        # Most probable exception is the service does not exists
        logging.info('Workspace {} is not active'.format(workspace))
        worker_deleted = False

    if worker_deleted:
        return jsonify('Workspace {} stopped'.format(workspace)), 200
    else:
        return jsonify('Workspace {} is not active'.format(workspace)), 400


if __name__ == '__main__':
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    component = os.getenv('INSTANCE', 'triggerflow-controller')

    # Make sure we log to the console
    stream_handler = logging.StreamHandler()
    formatter = logging.Formatter('[%(asctime)s.%(msecs)03dZ][%(levelname)s][triggerflow] %(message)s',
                                  datefmt="%Y-%m-%dT%H:%M:%S")
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    logging.info('Starting Triggerflow Controller for KEDA')

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

    logging.info('Loading Kubernetes config')
    config.load_incluster_config()
    k_v1_api = client.AppsV1Api()
    k_co_api = client.CustomObjectsApi()

    # Set triggerflow worker container image
    worker_container_image = os.getenv('TRIGGERFLOW_WORKER_CONTAINER_IMAGE',
                                       'docker.io/triggerflow/keda-worker:python-worker-v1')

    port = int(os.getenv('PORT', 8080))
    logging.info('Triggerflow service started on port {}'.format(port))

    # Create workspaces
    active_workspaces = trigger_storage.list_workspaces()
    for active_workspace in active_workspaces:
        try:
            create_keda_scaledobject(active_workspace)
        except Exception as e:
            logging.error('Error creating workspace {}: {}'.format(active_workspace, str(e)))
            logging.error(traceback.format_exc())

    port = int(os.getenv('PORT', 8080))
    logging.info('Triggerflow API started on port {}'.format(port))
    app.run(host='0.0.0.0', port=port, debug=True)
