"""
Based heavily on https://github.com/airflow-plugins/airflow_api_plugin
"""

import json
import os
import logging
import configparser
from datetime import datetime
import pytz
import yaml
from cryptography.fernet import Fernet

from werkzeug.exceptions import HTTPException, NotFound 

from flask import Blueprint, current_app, send_from_directory, abort, escape, request, Response
from sqlalchemy import or_
from airflow import settings
from airflow.exceptions import AirflowException, AirflowConfigException
from airflow.www.app import csrf
from airflow.models import DagBag, DagRun, Connection
from airflow.utils import timezone
from airflow.utils.dates import date_range as utils_date_range
from airflow.utils.state import State
from airflow.api.common.experimental import trigger_dag
from airflow.configuration import conf as airflow_conf

from hubmap_api.manager import blueprint as api_bp
from hubmap_api.manager import show_template

from hubmap_commons.hm_auth import AuthHelper, AuthCache, secured
#from hubmap_api.hm_auth import AuthHelper, AuthCache, secured

API_VERSION = 4

LOGGER = logging.getLogger(__name__)

airflow_conf.read(os.path.join(os.environ['AIRFLOW_HOME'], 'instance', 'app.cfg'))

# Tables of configuration elements needed at start-up.
# Config elements must be lowercase
NEEDED_ENV_VARS = [
    'AIRFLOW_CONN_INGEST_API_CONNECTION',
    'AIRFLOW_CONN_UUID_API_CONNECTION',
    'AIRFLOW_CONN_SEARCH_API_CONNECTION',
    'AIRFLOW_CONN_ENTITY_API_CONNECTION'
    ]
NEEDED_CONFIG_SECTIONS = [
    'ingest_map',
    ]
NEEDED_CONFIGS = [
    ('ingest_map', 'scan.and.begin.processing'),
    ('ingest_map', 'validate.upload'),
    ('hubmap_api_plugin', 'build_number'),
    ('connections', 'app_client_id'),
    ('connections', 'app_client_secret'),
    ('connections', 'docker_mount_path'),
    ('connections', 'src_path'),
    ('connections', 'output_group_name'),
    ('connections', 'workflow_scratch'),
    ('core', 'timezone'),
    ('core', 'fernet_key')
    ]

def check_config():
    # Check for needed configuration elements, since it's better to fail early
    dct = airflow_conf.as_dict(display_sensitive=True)
    failed = 0
    for elt in NEEDED_ENV_VARS:
        if elt not in os.environ:
            LOGGER.error('The environment variable {} is not set'.format(elt))
            failed += 1
    for key in NEEDED_CONFIG_SECTIONS + [a for a, b in NEEDED_CONFIGS]:
        if not (key in dct or key.upper() in dct):
            LOGGER.error('The configuration section {} does not exist'.format(key))
            failed += 1
    for key1, key2 in NEEDED_CONFIGS:
        sub_dct = dct[key1] if key1 in dct else dct[key1.upper()]
        if not (key2 in sub_dct or key2.upper() in sub_dct):
            LOGGER.error('The configuration parameter [{}] {} does not exist'.format(key1, key2))
            failed += 1
    assert failed == 0, 'ingest-pipeline plugin found {} configuration errors'.format(failed)
check_config()


def config(section, key):
    dct = airflow_conf.as_dict(display_sensitive=True)
    if section in dct:
        if key in dct[section]:
            rslt = dct[section][key]
        elif key.lower() in dct[section]:
            rslt = dct[section][key.lower()]
        elif key.upper() in dct[section]:
            rslt = dct[section][key.upper()]
        else:
            raise AirflowConfigException('No config entry for [{}] {}'.format(section, key))
        # airflow config reader leaves quotes, which we want to strip
        for qc in ['"', "'"]:
            if rslt.startswith(qc) and rslt.endswith(qc):
                rslt = rslt.strip(qc)
        return rslt
    else:
        raise AirflowConfigException('No config section [{}]'.format(section))


AUTH_HELPER = None
if not AuthHelper.isInitialized():
    AUTH_HELPER = AuthHelper.create(clientId=config('connections', 'app_client_id'), 
                                    clientSecret=config('connections', 'app_client_secret'))
else:
    AUTH_HELPER = authHelper.instance()


class HubmapApiInputException(Exception):
    pass


class HubmapApiConfigException(Exception):
    pass
 
 
class HubmapApiResponse:
 
    def __init__(self):
        pass
 
    STATUS_OK = 200
    STATUS_BAD_REQUEST = 400
    STATUS_UNAUTHORIZED = 401
    STATUS_NOT_FOUND = 404
    STATUS_SERVER_ERROR = 500
 
    @staticmethod
    def standard_response(status, payload):
        json_data = json.dumps({
            'response': payload
        })
        resp = Response(json_data, status=status, mimetype='application/json')
        return resp
 
    @staticmethod
    def success(payload):
        return HubmapApiResponse.standard_response(HubmapApiResponse.STATUS_OK, payload)
 
    @staticmethod
    def error(status, error):
        return HubmapApiResponse.standard_response(status, {
            'error': error
        })
 
    @staticmethod
    def bad_request(error):
        return HubmapApiResponse.error(HubmapApiResponse.STATUS_BAD_REQUEST, error)
 
    @staticmethod
    def not_found(error='Resource not found'):
        return HubmapApiResponse.error(HubmapApiResponse.STATUS_NOT_FOUND, error)
 
    @staticmethod
    def unauthorized(error='Not authorized to access this resource'):
        return HubmapApiResponse.error(HubmapApiResponse.STATUS_UNAUTHORIZED, error)
 
    @staticmethod
    def server_error(error='An unexpected problem occurred'):
        return HubmapApiResponse.error(HubmapApiResponse.STATUS_SERVER_ERROR, error)


@api_bp.route('/test')
@secured(groups="HuBMAP-read")
def api_test():
    token = None
    clientId=config('connections', 'app_client_id')
    print ("Client id: " + clientId)
    clientSecret=config('connections', 'app_client_secret')
    print ("Client secret: " + clientSecret)
    if 'MAUTHORIZATION' in request.headers:
        token = str(request.headers["MAUTHORIZATION"])[8:]
    elif 'AUTHORIZATION' in request.headers:
        token = str(request.headers["AUTHORIZATION"])[7:]
    print ("Token: " + token)
    return HubmapApiResponse.success({'api_is_alive': True})
 

@api_bp.route('/version')
def api_version():
    return HubmapApiResponse.success({'api': API_VERSION,
                                      'build': config('hubmap_api_plugin', 'build_number')})

 
def format_dag_run(dag_run):
    return {
        'run_id': dag_run.run_id,
        'dag_id': dag_run.dag_id,
        'state': dag_run.get_state(),
        'start_date': (None if not dag_run.start_date else str(dag_run.start_date)),
        'end_date': (None if not dag_run.end_date else str(dag_run.end_date)),
        'external_trigger': dag_run.external_trigger,
        'execution_date': str(dag_run.execution_date)
    }


def find_dag_runs(session, dag_id, dag_run_id, execution_date):
    qry = session.query(DagRun)
    qry = qry.filter(DagRun.dag_id == dag_id)
    qry = qry.filter(or_(DagRun.run_id == dag_run_id, DagRun.execution_date == execution_date))

    return qry.order_by(DagRun.execution_date).all()


def _get_required_string(data, st):
    """
    Return data[st] if present and a valid string; otherwise raise HubmapApiInputException
    """
    if st in data and data[st] is not None:
        return data[st]
    else:
        raise HubmapApiInputException(st)


def check_ingest_parms(provider, submission_id, process, full_path):
    """
    This routine performs consistency checks on the parameters of an ingest request.
    On error, HubmapApiInputException is raised.
    Return value is None.
    """
    if process.startswith('mock.'):
        # test request; there should be pre-recorded response data
        here_dir = os.path.dirname(os.path.resolve(__file__))
        yml_path = os.path.join(here_dir,'../../dags/mock_data/',
                                process + '.yml')
        try:
            with open(yml_path, 'r') as f:
                mock_data = yaml.safe_load(f)
        except yaml.YamlError as e:
            LOGGER.error('mock data contains invalid YAML: {}'.format(e))
            raise HubmapApiInputException('Mock data is invalid YAML for process %s', process)
        except IOError as e:
            LOGGER.error('mock data load failed: {}'.format(e))
            raise HubmapApiInputException('No mock data found for process %s', process)
    else:
        dct = {'provider' : provider, 'submission_id' : submission_id, 'process' : process}
        base_path = config('connections', 'docker_mount_path')
        if os.path.commonprefix([full_path, base_path]) != base_path:
            LOGGER.error("Ingest directory {} is not a subdirectory of DOCKER_MOUNT_PATH"
                         .format(full_path))
            raise HubmapApiInputException("Ingest directory is not a subdirectory of DOCKER_MOUNT_PATH")
        if os.path.exists(full_path) and os.path.isdir(full_path):
            try:
                num_files = len(os.listdir(full_path))
            except PermissionError as e:
                LOGGER.error("Permission error on ingest directory {}".format(full_path))
                raise HubmapApiInputException(str(e))
            if not num_files:
                LOGGER.error("Ingest directory {} contains no files".format(full_path))
                raise HubmapApiInputException("Ingest directory contains no files")
        else:
            LOGGER.error("cannot find the ingest data for '%s' '%s' '%s' (expected %s)"
                         % (provider, submission_id, process, full_path))
            raise HubmapApiInputException("Cannot find the expected ingest directory for '%s' '%s' '%s'"
                                          % (provider, submission_id, process))
    

def _auth_tok_from_request():
    """
    Parse out and return the authentication token from the current request
    """ 
    authorization = request.headers.get('authorization')
    LOGGER.info('top of request_ingest.')
    assert authorization[:len('BEARER')].lower() == 'bearer', 'authorization is not BEARER'
    substr = authorization[len('BEARER'):].strip()
    auth_tok = substr
    #LOGGER.info('auth_tok: %s', auth_tok)  # reduce visibility of auth_tok
    return auth_tok


def _auth_tok_from_environment():
    """
    Get the 'permanent authorization token'
    """
    tok = airflow_conf.as_dict()['connections']['APP_CLIENT_SECRET']
    return tok


def _get_dag(dag_id):
    """
    Look up and return the dag associated with this dag_id, or raise KeyError
    """
    dagbag = DagBag('dags')

    if dag_id not in dagbag.dags:
        LOGGER.warning('Requested dag {} not among {}'
                       .format(dag_id,[did for did in dagbag.dags]))
        LOGGER.warning('Dag dir full path {}'.os.path.abspath('dags'))
        raise KeyError(f"Dag id {dag_id} not found")
    return dagbag.get_dag(dag_id)


"""
Parameters for this request (all required)

Key            Method    Type    Description
provider        post    string    Providing site, presumably a known TMC
submission_id   post    string    Unique ID string specifying this dataset
process         post    string    string denoting a unique known processing workflow to be applied to this data
full_path       post    string    full path to the root of the dataset file directory tree

Parameters included in the response:
Key        Type    Description
ingest_id  string  Unique ID string to be used in references to this request
run_id     string  The identifier by which the ingest run is known to Airflow
"""
@csrf.exempt
@api_bp.route('/request_ingest', methods=['POST'])
#@secured(groups="HuBMAP-read")
def request_ingest():
    auth_tok = _auth_tok_from_environment()

    # decode input
    data = request.get_json(force=True)
    
    LOGGER.debug('request_ingest data: {}'.format(str(data)))
    # Test and extract required parameters
    try:
        provider = _get_required_string(data, 'provider')
        submission_id = _get_required_string(data, 'submission_id')
        process = _get_required_string(data, 'process')
        full_path = _get_required_string(data, 'full_path')
    except HubmapApiInputException as e:
        return HubmapApiResponse.bad_request('Must specify {} to request data be ingested'.format(str(e)))

    process = process.lower()  # necessary because config parser has made the corresponding string lower case

    try:
        dag_id = config('ingest_map', process)
    except HubmapApiConfigException:
        return HubmapApiResponse.bad_request('{} is not a known ingestion process'.format(process))
    
    try:
        check_ingest_parms(provider, submission_id, process, full_path)
    
        session = settings.Session()

        try:
            dag = _get_dag(dag_id)
        except KeyError as e:
            HubmapApiResponse.not_found(f'{e}')

        # Produce one and only one run
        tz = pytz.timezone(config('core', 'timezone'))
        execution_date = datetime.now(tz)
        LOGGER.info('starting {} with execution_date: {}'.format(dag_id,
                                                                 execution_date))

        run_id = '{}_{}_{}'.format(submission_id, process, execution_date.isoformat())
        ingest_id = run_id
        fernet = Fernet(config('core', 'fernet_key').encode())
        crypt_auth_tok = fernet.encrypt(auth_tok.encode()).decode()

        conf = {'provider': provider,
                'submission_id': submission_id,
                'process': process,
                'dag_id': dag_id,
                'run_id': run_id,
                'ingest_id': ingest_id,
                'crypt_auth_tok': crypt_auth_tok,
                'src_path': config('connections', 'src_path'),
                'lz_path': full_path
                }

        if find_dag_runs(session, dag_id, run_id, execution_date):
            # The run already happened??
            raise AirflowException('The request happened twice?')

        try:
            dr = trigger_dag.trigger_dag(dag_id, run_id, conf, execution_date=execution_date)
        except AirflowException as err:
            LOGGER.error(err)
            raise AirflowException("Attempt to trigger run produced an error: {}".format(err))
        LOGGER.info('dagrun follows: {}'.format(dr))

#             dag.create_dagrun(
#                 run_id=run['run_id'],
#                 execution_date=run['execution_date'],
#                 state=State.RUNNING,
#                 conf=conf,
#                 external_trigger=True
#             )
#            results.append(run['run_id'])

        session.close()
    except HubmapApiInputException as e:
        return HubmapApiResponse.bad_request(str(e))
    except ValueError as e:
        return HubmapApiResponse.server_error(str(e))
    except AirflowException as e:
        return HubmapApiResponse.server_error(str(e))
    except Exception as e:
        return HubmapApiResponse.server_error(str(e))

    return HubmapApiResponse.success({'ingest_id': ingest_id,
                                      'run_id': run_id})


def generic_invoke_dag_on_uuid(uuid, process_name):
    auth_tok = _auth_tok_from_environment()
    process = process_name
    try:
        dag_id = config('ingest_map', process)
        session = settings.Session()
        dag = _get_dag(dag_id)

        # Produce one and only one run
        tz = pytz.timezone(config('core', 'timezone'))
        execution_date = datetime.now(tz)
        LOGGER.info('starting {} with execution_date: {}'.format(dag_id,
                                                                 execution_date))

        run_id = '{}_{}_{}'.format(uuid, process, execution_date.isoformat())
        fernet = Fernet(config('core', 'fernet_key').encode())
        crypt_auth_tok = fernet.encrypt(auth_tok.encode()).decode()

        conf = {'process': process,
                'dag_id': dag_id,
                'run_id': run_id,
                'crypt_auth_tok': crypt_auth_tok,
                'src_path': config('connections', 'src_path'),
                'uuid': uuid
                }

        if find_dag_runs(session, dag_id, run_id, execution_date):
            # The run already happened??
            raise AirflowException('The request happened twice?')

        try:
            dr = trigger_dag.trigger_dag(dag_id, run_id, conf, execution_date=execution_date)
        except AirflowException as err:
            LOGGER.error(err)
            raise AirflowException("Attempt to trigger run produced an error: {}".format(err))
        LOGGER.info('dagrun follows: {}'.format(dr))

        session.close()
    except HubmapApiConfigException:
        return HubmapApiResponse.bad_request(f'{process} does not map to a known DAG')
    except HubmapApiInputException as e:
        return HubmapApiResponse.bad_request(str(e))
    except ValueError as e:
        return HubmapApiResponse.server_error(str(e))
    except KeyError as e:
        HubmapApiResponse.not_found(f'{e}')
    except AirflowException as e:
        return HubmapApiResponse.server_error(str(e))
    except Exception as e:
        return HubmapApiResponse.server_error(str(e))

    return HubmapApiResponse.success({'run_id': run_id})


@csrf.exempt
@api_bp.route('/uploads/<uuid>/validate', methods=['PUT'])
#@secured(groups="HuBMAP-read")
def validate_upload_uuid(uuid):
    return generic_invoke_dag_on_uuid(uuid, 'validate.upload')
    auth_tok = _auth_tok_from_request()
    process = 'validate.upload'


@csrf.exempt
@api_bp.route('/uploads/<uuid>/reorganize', methods=['PUT'])
#@secured(groups="HuBMAP-read")
def reorganize_upload_uuid(uuid):
    return generic_invoke_dag_on_uuid(uuid, 'reorganize.upload')
    
    
"""
Parameters for this request: None

Parameters included in the response:
Key        Type    Description
process_strings  list of strings  The list of valid 'process' strings
"""
@api_bp.route('get_process_strings')
def get_process_strings():
    dct = airflow_conf.as_dict()
    psl = [s.upper() for s in dct['ingest_map']] if 'ingest_map' in dct else []
    return HubmapApiResponse.success({'process_strings': psl})

