import json
from json import JSONDecodeError

import jsonschema
import requests
import yaml
from yaml.scanner import ScannerError

from neoload_cli_lib import cli_exception, bad_as_code_exception
from neoload_cli_lib.user_data import update_schema, get_yaml_schema, tools

import logging
import hashlib
import os
from gitignore_parser import parse_gitignore
from neoload_cli_lib.neoLoad_project import is_not_to_be_included

YAML_NOT_CONFIRM_MESSAGE = "YAML does not confirm to NeoLoad DSL schema."
__default_schema_url = "https://raw.githubusercontent.com/Neotys-Labs/neoload-models/v3/neoload-project/src/main/resources/as-code.latest.schema.json"

def validate_yaml(yaml_file_path, schema_spec, ssl_cert='', check_schema=True):
    json_schema = init_yaml_schema_with_checks(schema_spec,ssl_cert,check_schema)
    try:
        schema_as_object = json.loads(json_schema)
    except JSONDecodeError as err:
        raise bad_as_code_exception.BadAsCodeSchemaException(
            'This is not a valid json schema [{}] :\n{}'.format(schema_spec, err))

    try:
        yaml_content = open(yaml_file_path)
    except Exception as err:
        raise cli_exception.CliException('Unable to open file %s:\n%s' % (yaml_file_path, str(err)))

    try:
        yaml_as_object = yaml.load(yaml_content, yaml.FullLoader)
        if yaml_as_object is None:
            raise cli_exception.CliException('Empty file: ' + str(yaml_file_path))
    except ScannerError as err:
        raise cli_exception.CliException('This is not a valid yaml file [{}] :\n{}'.format(yaml_file_path,err))

    v = jsonschema.validators.Draft7Validator(schema_as_object)
    try:
        v.validate(yaml_as_object)
    except jsonschema.SchemaError as err:
        raise cli_exception.CliException('This is not a valid json schema:\n%s' % str(err))
    except jsonschema.ValidationError as err:
        msgs = ""
        for error in sorted(v.iter_errors(yaml_as_object), key=str):
            path = "\\".join(list(map(lambda x: str(x), error.path)))
            msgs += "\n" + (error.message if hasattr(error, 'message') else str(error)) + "\n\tat: " + path + "\n\tgot: \n" + (yaml.dump(error.instance) if hasattr(error, 'instance') else '') + "\n"
        msgs = ("in file %s" % yaml_file_path) + msgs
        raise cli_exception.CliException(YAML_NOT_CONFIRM_MESSAGE + '\n' + msgs)


def validate_yaml_dir(path, schema_spec, ssl_cert='',continue_on_error=True):
    ignore_file = os.path.join(path, '.nlignore')
    nl_ignore_matcher = parse_gitignore(ignore_file) if os.path.exists(ignore_file) else None
    first_time_check = True
    extensions = ['yml','yaml','json']
    any_errs = False
    for root, dirs, files in os.walk(path):
        for file in files:
            file_path = os.path.join(root, file)
            (any_errs,first_time_check) = validate_yaml_dir_file(file_path,schema_spec,extensions,nl_ignore_matcher,any_errs,first_time_check,continue_on_error,ssl_cert)

    if any_errs:
        raise ValueError('One or more errors in files underneath this directory.')

def validate_yaml_dir_file(file_path,schema_spec,extensions,nl_ignore_matcher,any_errs,first_time_check,continue_on_error,ssl_cert):

    if any(filter(lambda ext,file_path=file_path: file_path.endswith("."+ext),extensions)) and \
       not is_not_to_be_included(file_path, nl_ignore_matcher):
        logging.debug("file_path: {}".format(file_path))
        try:
            validate_yaml(file_path, schema_spec, ssl_cert, check_schema=first_time_check)
        except ValueError as err:
            any_errs = True
            logging.error("INFOMSG:%s" % str(err))
        except Exception as err:
            any_errs = True
            if continue_on_error and not isinstance(err, bad_as_code_exception.BadAsCodeSchemaException):
                logging.error(str(err) + "\n")
            else:
                raise err
        first_time_check = False

    return (any_errs,first_time_check)


def init_yaml_schema_with_checks(schema_spec, ssl_cert='', check_schema=True):
    json_schema = get_yaml_schema(False)
    if json_schema is not None:
        logging.info('Loaded schema from disk.')
    else:
        logging.warning('No prior cached schema on disk.')

    if json_schema is not None:
        logging.debug("Cached schema %s" %len(json_schema))

    if not check_schema:
        return json_schema

    # even if there is something local, try checking if it's different from remote
    schema_spec_remote = __default_schema_url
    if schema_spec is None: schema_spec = schema_spec_remote
    logging.debug("Getting remote schema %s" %schema_spec)
    json_schema_spec = get_json_schema_by_spec(schema_spec,ssl_cert)
    if json_schema_spec is not None:
        logging.debug("Retrieved remote schema %s" %len(json_schema_spec))

    # compare cached to spec/remote
    try:
        logging.info('Comparing cached schema to remote schema')
        hash_disk = "" if json_schema is None else hashlib.sha256(json_schema.encode()).hexdigest()
        hash_spec = "" if json_schema_spec is None else hashlib.sha256(json_schema_spec.encode()).hexdigest()
        if hash_disk != hash_spec:
            logging.info('Cached schema differs from source!')
            json_schema = json_schema_spec
            update_schema(json_schema_spec)
        else:
            logging.info('No differences between cached and remote schema.')
    except Exception as err:
        logging.warning('Could not update schema cache {}\n{}'.format(schema_spec,err))

    if json_schema is None:
        raise bad_as_code_exception.BadAsCodeSchemaException('Could not obtain schema definition therefore could not validate this schema.')

    return json_schema


def get_json_schema_by_spec(schema_spec, ssl_cert):
    json_schema_spec = None

    if type(schema_spec).__name__ == 'LocalPath':
        schema_spec = schema_spec.strpath

    if '://' in schema_spec:
        try:
            logging.info('Getting remote schema from network source %s' % schema_spec)
            json_schema_spec = requests.get(schema_spec, verify=tools.ssl_cert_to_verify(ssl_cert)).text
        except Exception as err:
            logging.warning('Could not obtain source schema {}\n{}'.format(schema_spec,err))
    else:
        # if user passed in a local file as the --schema-url (for local version testing purposes too)
        schema_spec = os.path.abspath(schema_spec)
        if os.path.exists(schema_spec):
            with open(schema_spec, "r") as stream:
                logging.info('Reading remote schema from storage source %s' % schema_spec)
                json_schema_spec = stream.read()
        else:
            raise bad_as_code_exception.BadAsCodeSchemaException('Could not load schema from provided file spec: %s' % schema_spec)

    return json_schema_spec
