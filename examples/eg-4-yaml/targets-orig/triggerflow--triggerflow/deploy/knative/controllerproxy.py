import yaml
import logging
from flask import Flask, jsonify, request
from kubernetes import client, config, watch
from redis_db import RedisDatabase

logger = logging.getLogger('triggerflow-controller')

app = Flask(__name__)

config_map = None
db = None
k_v1_api = None
k_co_api = None

service_res = """
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: triggerflow-knative-worker
  #namespace: default
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/minScale: "1"
        autoscaling.knative.dev/maxScale: "1"
    spec:
      #containerConcurrency: 1
      #timeoutSeconds: 300
      containers:
        - image: jsampe/triggerflow-knative-worker
          env:
          - name: workspace
            value: 'default'
          resources:
            limits:
              memory: 1Gi
              cpu: 1
"""

event_source_res = """
apiVersion: sources.knative.dev/v1alpha1
kind: KafkaSource
metadata:
  name: kafka-source
spec:
  consumerGroup: triggerflow
  bootstrapServers: IP:PORT
  topics: topic-name
  sink:
    #apiVersion: serving.knative.dev/v1
    #kind: Service
    #name: event-display
    apiVersion: eventing.knative.dev/v1alpha1
    kind: Broker
    name: default
    #apiVersion: messaging.knative.dev/v1alpha1
    #kind: Channel
    #name: triggerflow-channel
    #kind: KafkaChannel
    #name: triggerflow-kafka-channel
  resources:
    requests:
      memory: 512Mi
      cpu: 1000m
"""

trigger_res = """
apiVersion: eventing.knative.dev/v1alpha1
kind: Trigger
metadata:
  name: triggerflow-worker-trigger
spec:
  subscriber:
    ref:
      apiVersion: serving.knative.dev/v1
      kind: Service
      #name: event-display
      name: triggerflow-worker-pywren
"""


def authenticate_request(db, auth):
    if not auth or \
       'username' not in auth \
       or 'password' not in auth:
        return False

    passwd = db.get_auth(username=auth['username'])
    return passwd and passwd == auth['password']


@app.before_request
def before_request_func():
    if not authenticate_request(db, request.auth):
        return jsonify('Unauthorized'), 401


@app.route('/workspace/<workspace>', methods=['POST'])
def create_workspace(workspace):
    """
    This method gets the request parameters and starts a new thread worker
    that will act as the event-processor for the the specific trigger workspace.
    It returns 400 error if the provided parameters are not correct.
    """
    if not db.workspace_exists(workspace):
        return jsonify('Workspace {} does not exists in the database'.format(workspace)), 400

    print('New request to create workspace {}'.format(workspace))

    if create_knative_service(workspace):
        return jsonify('Created workspace {}'.format(workspace)), 201
    else:
        return jsonify('Workspace {} is already created'.format(workspace)), 400


def create_knative_service(workspace):

    svc_res = yaml.safe_load(service_res)

    service_name = 'triggerflow-worker-{}'.format(workspace)
    svc_res['metadata']['name'] = service_name
    svc_res['spec']['template']['spec']['containers'][0]['env'][0]['value'] = workspace

    try:
        # create the service resource
        k_co_api.create_workspaced_custom_object(
                group="serving.knative.dev",
                version="v1",
                namespace='default',
                plural="services",
                body=svc_res
            )

        w = watch.Watch()
        for event in w.stream(k_co_api.list_workspaced_custom_object,
                              namespace='default', group="serving.knative.dev",
                              version="v1", plural="services",
                              field_selector="metadata.name={0}".format(service_name)):
            conditions = None
            if event['object'].get('status'):
                conditions = event['object']['status']['conditions']
                if event['object']['status'].get('url') is not None:
                    service_url = event['object']['status']['url']
            if conditions and conditions[0]['status'] == 'True' and \
               conditions[1]['status'] == 'True' and conditions[2]['status'] == 'True':
                w.stop()

        print('Trigger Service worker created - URL: {}'.format(service_url))
        worker_created = True
    except Exception as e:
        print('Warning: {}'.format(str(e)))
        worker_created = False

    try:
        # Create event sources
        print('Starting event sources...')
        event_sources = db.get(workspace, 'event_sources')
        for evt_src in event_sources.values():
            if evt_src['class'] == 'KafkaCloudEventSource':
                print('Starting {}'.format(evt_src['name']))
                es_res = yaml.safe_load(event_source_res)
                es_res['metadata']['name'] = evt_src['name']
                es_res['spec']['bootstrapServers'] = ','.join(evt_src['spec']['broker_list'])
                es_res['spec']['topics'] = evt_src['spec']['topic']
                # es_res['spec']['sink']['name'] = service_name

                # create the service resource
                k_co_api.create_workspaced_custom_object(
                        group="sources.knative.dev",
                        version="v1alpha1",
                        namespace='default',
                        plural="kafkasources",
                        body=es_res
                    )

                w = watch.Watch()
                for event in w.stream(k_co_api.list_workspaced_custom_object,
                                      namespace='default', group="sources.knative.dev",
                                      version="v1alpha1", plural="kafkasources",
                                      field_selector="metadata.name={0}".format(evt_src['name'])):
                    conditions = None
                    if event['object'].get('status'):
                        conditions = event['object']['status']['conditions']
                        if event['object']['status'].get('url') is not None:
                            service_url = event['object']['status']['url']
                    if conditions and conditions[0]['status'] == 'True' and \
                       conditions[1]['status'] == 'True' and conditions[2]['status'] == 'True':
                        w.stop()
            else:
                return jsonify('Not supported event source: {}'.format(evt_src['class'])), 400
        print('Event source started')
    except Exception as e:
        print('Warning: {}'.format(str(e)))

    return worker_created


@app.route('/workspace/<workspace>', methods=['DELETE'])
def delete_workspace(workspace):
    if not authenticate_request(db, request):
        return jsonify('Unauthorized'), 401

    print('Stopping workspace: {}'.format(workspace))
    try:
        # delete the service resource if exists
        service_name = 'triggerflow-worker-{}'.format(workspace)
        k_co_api.delete_workspaced_custom_object(
                group="serving.knative.dev",
                version="v1",
                name=service_name,
                namespace='default',
                plural="services",
                body=client.V1DeleteOptions()
            )
        print('Workspace {} stopped'.format(workspace))
        worker_deleted = True
    except Exception:
        # Most probable exception is the service does not exists
        print('Workspace {} is not active'.format(workspace))
        worker_deleted = False

    # Stop event sources
    event_sources = db.get(database_name=workspace, document_id='.event_sources')
    print('Stopping event sources for workspace {}'.format(workspace))
    for evt_src in event_sources.values():
        if evt_src['class'] == 'KafkaCloudEventSource':
            print('Stopping {}'.format(evt_src['name']))
            try:
                k_co_api.delete_workspaced_custom_object(
                        group="sources.knative.dev",
                        version="v1alpha1",
                        name=evt_src['name'],
                        namespace='default',
                        plural="kafkasources",
                        body=client.V1DeleteOptions()
                    )
            except Exception:
                pass
    print('Event sources for workspace {} stopped'.format(workspace))

    if worker_deleted:
        return jsonify('Workspace {} stopped'.format(workspace)), 200
    else:
        return jsonify('Workspace {} is not active'.format(workspace)), 400


def main():
    print('Starting Triggerflow controller')

    global config_map, db, k_v1_api, k_co_api

    print('Loading private credentials')
    with open('config.yaml', 'r') as config_file:
        private_credentials = yaml.safe_load(config_file)

    print('Creating DB connection')
    db = RedisDatabase(**private_credentials['redis'])

    print('loading kubernetes config')
    config.load_incluster_config()
    k_v1_api = client.CoreV1Api()
    k_co_api = client.CustomObjectsApi()

    workspaces = db.list_workspaces()
    if workspaces:
        for wsp in workspaces:
            print('Starting {} workspace...'.format(wsp))
            create_knative_service(wsp)

    print('Triggerflow controller started')


main()
