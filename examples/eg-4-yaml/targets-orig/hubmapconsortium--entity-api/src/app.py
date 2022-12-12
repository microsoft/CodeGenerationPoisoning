import collections
import yaml
from datetime import datetime
from flask import Flask, g, jsonify, abort, request, Response, redirect, make_response
from neo4j.exceptions import TransactionError
import os
import re
import csv
import requests
import urllib.request
from io import StringIO
# Don't confuse urllib (Python native library) with urllib3 (3rd-party library, requests also uses urllib3)
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from pathlib import Path
import logging
import json
import time

# Local modules
import app_neo4j_queries
import provenance
from schema import schema_manager
from schema import schema_errors
from schema import schema_triggers
from schema.schema_constants import SchemaConstants

# HuBMAP commons
from hubmap_commons import string_helper
from hubmap_commons import file_helper as hm_file_helper
from hubmap_commons import neo4j_driver
from hubmap_commons import globus_groups
from hubmap_commons.hm_auth import AuthHelper
from hubmap_commons.exceptions import HTTPException


# Root logger configuration
global logger

# Use `getLogger()` instead of `getLogger(__name__)` to apply the config to the root logger
# will be inherited by the sub-module loggers
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# All the API logging is gets written into the same log file
# The uWSGI logging for each deployment disables the request logging
# but still captures the 4xx and 5xx errors to the file `log/uwsgi-entity-api.log`
# Log rotation is handled via logrotate on the host system with a configuration file
# Do NOT handle log file and rotation via the Python logging to avoid issues with multi-worker processes
log_file_handler = logging.FileHandler('../log/entity-api-' + time.strftime("%m-%d-%Y-%H-%M-%S") + '.log')
log_file_handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s'))
logger.addHandler(log_file_handler)

# Specify the absolute path of the instance folder and use the config file relative to the instance path
app = Flask(__name__, instance_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance'), instance_relative_config = True)
app.config.from_pyfile('app.cfg')

# Remove trailing slash / from URL base to avoid "//" caused by config with trailing slash
app.config['UUID_API_URL'] = app.config['UUID_API_URL'].strip('/')
app.config['INGEST_API_URL'] = app.config['INGEST_API_URL'].strip('/')
app.config['SEARCH_API_URL_LIST'] = [url.strip('/') for url in app.config['SEARCH_API_URL_LIST']]

# Suppress InsecureRequestWarning warning when requesting status on https with ssl cert verify disabled
requests.packages.urllib3.disable_warnings(category = InsecureRequestWarning)

# For performance improvement and not overloading the server, especially helpful during Elasticsearch index/reindex
entity_cache = {}


####################################################################################################
## Register error handlers
####################################################################################################

# Error handler for 400 Bad Request with custom error message
@app.errorhandler(400)
def http_bad_request(e):
    return jsonify(error = str(e)), 400


# Error handler for 401 Unauthorized with custom error message
@app.errorhandler(401)
def http_unauthorized(e):
    return jsonify(error = str(e)), 401


# Error handler for 403 Forbidden with custom error message
@app.errorhandler(403)
def http_forbidden(e):
    return jsonify(error = str(e)), 403


# Error handler for 404 Not Found with custom error message
@app.errorhandler(404)
def http_not_found(e):
    return jsonify(error = str(e)), 404


# Error handler for 500 Internal Server Error with custom error message
@app.errorhandler(500)
def http_internal_server_error(e):
    return jsonify(error = str(e)), 500


####################################################################################################
## AuthHelper initialization
####################################################################################################

# Initialize AuthHelper class and ensure singleton
try:
    if AuthHelper.isInitialized() == False:
        auth_helper_instance = AuthHelper.create(app.config['APP_CLIENT_ID'],
                                                 app.config['APP_CLIENT_SECRET'])

        logger.info("Initialized AuthHelper class successfully :)")
    else:
        auth_helper_instance = AuthHelper.instance()
except Exception:
    msg = "Failed to initialize the AuthHelper class"
    # Log the full stack trace, prepend a line with our message
    logger.exception(msg)


####################################################################################################
## Neo4j connection initialization
####################################################################################################

# The neo4j_driver (from commons package) is a singleton module
# This neo4j_driver_instance will be used for application-specifc neo4j queries
# as well as being passed to the schema_manager
try:
    neo4j_driver_instance = neo4j_driver.instance(app.config['NEO4J_URI'],
                                                  app.config['NEO4J_USERNAME'],
                                                  app.config['NEO4J_PASSWORD'])
    logger.info("Initialized neo4j_driver module successfully :)")
except Exception:
    msg = "Failed to initialize the neo4j_driver module"
    # Log the full stack trace, prepend a line with our message
    logger.exception(msg)


"""
Close the current neo4j connection at the end of every request
"""
@app.teardown_appcontext
def close_neo4j_driver(error):
    if hasattr(g, 'neo4j_driver_instance'):
        # Close the driver instance
        neo4j_driver.close()
        # Also remove neo4j_driver_instance from Flask's application context
        g.neo4j_driver_instance = None


####################################################################################################
## Schema initialization
####################################################################################################

try:
    # The schema_manager is a singleton module
    # Pass in auth_helper_instance, neo4j_driver instance, and file_upload_helper instance
    schema_manager.initialize(app.config['SCHEMA_YAML_FILE'],
                              app.config['UUID_API_URL'],
                              app.config['INGEST_API_URL'],
                              auth_helper_instance,
                              neo4j_driver_instance)

    logger.info("Initialized schema_manager module successfully :)")
# Use a broad catch-all here
except Exception:
    msg = "Failed to initialize the schema_manager module"
    # Log the full stack trace, prepend a line with our message
    logger.exception(msg)


####################################################################################################
## REFERENCE DOI Redirection
####################################################################################################

## Read tsv file with the REFERENCE entity redirects
## sets the reference_redirects dict which is used
## by the /redirect method below
try:
    reference_redirects = {}
    url = app.config['REDIRECTION_INFO_URL']
    response = requests.get(url)
    resp_txt = response.content.decode('utf-8')
    cr = csv.reader(resp_txt.splitlines(), delimiter='\t')

    first = True
    id_column = None
    redir_url_column = None
    for row in cr:
        if first:
            first = False
            header = row
            column = 0
            for label in header:
                if label == 'hubmap_id': id_column = column
                if label == 'data_information_page': redir_url_column = column
                column = column + 1
            if id_column is None: raise Exception(f"Column hubmap_id not found in {url}")
            if redir_url_column is None: raise Exception (f"Column data_information_page not found in {url}")
        else:
            reference_redirects[row[id_column].upper().strip()] = row[redir_url_column]
    rr = redirect('abc', code = 307)
    print(rr)
except Exception:
    logger.exception("Failed to read tsv file with REFERENCE redirect information")


####################################################################################################
## Constants
####################################################################################################

# For now, don't use the constants from commons
# All lowercase for easy comparision
ACCESS_LEVEL_PUBLIC = 'public'
ACCESS_LEVEL_CONSORTIUM = 'consortium'
ACCESS_LEVEL_PROTECTED = 'protected'
DATASET_STATUS_PUBLISHED = 'published'
COMMA_SEPARATOR = ','


####################################################################################################
## API Endpoints
####################################################################################################

"""
The default route

Returns
-------
str
    A welcome message
"""
@app.route('/', methods = ['GET'])
def index():
    return "Hello! This is HuBMAP Entity API service :)"


"""
Show status of neo4j connection with the current VERSION and BUILD

Returns
-------
json
    A json containing the status details
"""
@app.route('/status', methods = ['GET'])
def get_status():
    status_data = {
        # Use strip() to remove leading and trailing spaces, newlines, and tabs
        'version': (Path(__file__).absolute().parent.parent / 'VERSION').read_text().strip(),
        'build': (Path(__file__).absolute().parent.parent / 'BUILD').read_text().strip(),
        'neo4j_connection': False
    }

    # Don't use try/except here
    is_connected = app_neo4j_queries.check_connection(neo4j_driver_instance)

    if is_connected:
        status_data['neo4j_connection'] = True

    return jsonify(status_data)


"""
Currently for debugging purpose 
Essentially does the same as ingest-api's `/metadata/usergroups` using the deprecated commons method
Globus groups token is required by AWS API Gateway lambda authorizer

Returns
-------
json
    A json list of globus groups this user belongs to
"""
@app.route('/usergroups', methods = ['GET'])
def get_user_groups():
    token = get_user_token(request)
    groups_list = auth_helper_instance.get_user_groups_deprecated(token)
    return jsonify(groups_list)


"""
Retrieve the ancestor organ(s) of a given entity

The gateway treats this endpoint as public accessible

Parameters
----------
id : str
    The HuBMAP ID (e.g. HBM123.ABCD.456) or UUID of target entity (Dataset/Sample)

Returns
-------
json
    List of organs that are ancestors of the given entity
    - Only dataset entities can return multiple ancestor organs
      as Samples can only have one parent.
    - If no organ ancestors are found an empty list is returned
    - If requesting the ancestor organ of a Sample of type Organ or Donor/Collection/Upload
      a 400 response is returned.
"""
@app.route('/entities/<id>/ancestor-organs', methods = ['GET'])
def get_ancestor_organs(id):
    # Token is not required, but if an invalid token provided,
    # we need to tell the client with a 401 error
    validate_token_if_auth_header_exists(request)

    # Use the internal token to query the target entity
    # since public entities don't require user token
    token = get_internal_token()

    # Get the entity dict from cache if exists
    # Otherwise query against uuid-api and neo4j to get the entity dict if the id exists
    entity_dict = query_target_entity(id, token)
    normalized_entity_type = entity_dict['entity_type']

    # A bit validation
    supported_entity_types = ['Sample', 'Dataset']
    if normalized_entity_type not in supported_entity_types:
        bad_request_error(f"Unable to get the ancestor organs for this: {normalized_entity_type}, supported entity types: {COMMA_SEPARATOR.join(supported_entity_types)}")

    if normalized_entity_type == 'Sample' and entity_dict['specimen_type'].lower() == 'organ':
        bad_request_error("Unable to get the ancestor organ of an organ.")

    if normalized_entity_type == 'Dataset':
        # Only published/public datasets don't require token
        if entity_dict['status'].lower() != DATASET_STATUS_PUBLISHED:
            # Token is required and the user must belong to HuBMAP-READ group
            token = get_user_token(request, non_public_access_required = True)
    else:
        # The `data_access_level` of Sample can only be either 'public' or 'consortium'
        if entity_dict['data_access_level'] == ACCESS_LEVEL_CONSORTIUM:
            token = get_user_token(request, non_public_access_required = True)

    # By now, either the entity is public accessible or the user token has the correct access level
    organs = app_neo4j_queries.get_ancestor_organs(neo4j_driver_instance, entity_dict['uuid'])

    # Skip executing the trigger method to get Sample.direct_ancestor
    properties_to_skip = ['direct_ancestor']
    complete_entities_list = schema_manager.get_complete_entities_list(token, organs, properties_to_skip)

    # Final result after normalization
    final_result = schema_manager.normalize_entities_list_for_response(complete_entities_list)

    return jsonify(final_result)


"""
Retrive the metadata information of a given entity by id

The gateway treats this endpoint as public accessible

Result filtering is supported based on query string
For example: /entities/<id>?property=data_access_level

Parameters
----------
id : str
    The HuBMAP ID (e.g. HBM123.ABCD.456) or UUID of target entity 

Returns
-------
json
    All the properties or filtered property of the target entity
"""
@app.route('/entities/<id>', methods = ['GET'])
def get_entity_by_id(id):
    # Token is not required, but if an invalid token provided,
    # we need to tell the client with a 401 error
    validate_token_if_auth_header_exists(request)

    # Use the internal token to query the target entity
    # since public entities don't require user token
    token = get_internal_token()

    # Get the entity dict from cache if exists
    # Otherwise query against uuid-api and neo4j to get the entity dict if the id exists
    entity_dict = query_target_entity(id, token)
    normalized_entity_type = entity_dict['entity_type']

    # Handle Collection retrieval using a different endpoint
    if normalized_entity_type == 'Collection':
        bad_request_error("Please use another API endpoint `/collections/<id>` to query a collection")

    if normalized_entity_type == 'Dataset':
        # Only published/public datasets don't require token
        if entity_dict['status'].lower() != DATASET_STATUS_PUBLISHED:
            # Token is required and the user must belong to HuBMAP-READ group
            token = get_user_token(request, non_public_access_required = True)
    elif normalized_entity_type == 'Upload':
        # Upload doesn't have 'data_access_level' property
        # Always require at least consortium group token for accessing Upload
        token = get_user_token(request, non_public_access_required = True)
    else:
        # The `data_access_level` of Donor/Sample can only be either 'public' or 'consortium'
        if entity_dict['data_access_level'] == ACCESS_LEVEL_CONSORTIUM:
            token = get_user_token(request, non_public_access_required = True)

    # By now, either the entity is public accessible or the user token has the correct access level
    # We'll need to return all the properties including those
    # generated by `on_read_trigger` to have a complete result
    # E.g., the 'next_revision_uuid' and 'previous_revision_uuid' being used below
    # On entity retrieval, the 'on_read_trigger' doesn't really need a token
    complete_dict = schema_manager.get_complete_entity_result(token, entity_dict)

    # Additional handlings on dataset revisions
    # The rule is that a revision can only be made against a published dataset,
    # so it should never occur that a consortium level revision is between two published revisions
    # However, the very last dataset revision can be non-published
    if normalized_entity_type == 'Dataset':
        # The `next_revision_uuid` is only availabe in complete_dict because it's generated by the 'on_read_trigger'
        property_to_pop = 'next_revision_uuid'

        # When the dataset is published but:
        # - There's no Authorization header thus no token
        # - The groups token is valid but the user doesn't belong to HuBMAP-READ group
        # - Or the token is valid but doesn't contain group information (auth token or transfer token)
        # We need to remove the `next_revision_uuid` from response
        # Otherwise, we should send back the `next_revision_uuid` (if exists) when the member belongs to HuBMAP-Read group
        if entity_dict['status'].lower() == DATASET_STATUS_PUBLISHED:
            if not user_in_hubmap_read_group(request):
                if property_to_pop in complete_dict:
                    revision_entity_dict = query_target_entity(complete_dict[property_to_pop], token)
                    # Remove the property from the resulting complete_dict
                    # if the revision is not published
                    if revision_entity_dict['status'].lower() != DATASET_STATUS_PUBLISHED:
                        complete_dict.pop(property_to_pop)
        # Non-published dataset can NOT have next revisions
        else:
            if property_to_pop in complete_dict:
                # Remove the `next_revision_uuid` from response if it ever exists
                complete_dict.pop(property_to_pop)

    # Also normalize the result based on schema
    final_result = schema_manager.normalize_entity_result_for_response(complete_dict)

    # Result filtering based on query string
    # The `data_access_level` property is available in all entities Donor/Sample/Dataset
    # and this filter is being used by gateway to check the data_access_level for file assets
    # The `status` property is only available in Dataset and being used by search-api for revision
    result_filtering_accepted_property_keys = ['data_access_level', 'status']

    if bool(request.args):
        property_key = request.args.get('property')

        if property_key is not None:
            # Validate the target property
            if property_key not in result_filtering_accepted_property_keys:
                bad_request_error(f"Only the following property keys are supported in the query string: {COMMA_SEPARATOR.join(result_filtering_accepted_property_keys)}")

            if property_key == 'status' and normalized_entity_type != 'Dataset':
                bad_request_error(f"Only Dataset supports 'status' property key in the query string")

            # Response with the property value directly
            # Don't use jsonify() on string value
            return complete_dict[property_key]
        else:
            bad_request_error("The specified query string is not supported. Use '?property=<key>' to filter the result")
    else:
        # Response with the dict
        return jsonify(final_result)


"""
Retrive the full tree above the referenced entity and build the provenance document

The gateway treats this endpoint as public accessible

Parameters
----------
id : str
    The HuBMAP ID (e.g. HBM123.ABCD.456) or UUID of target entity 

Returns
-------
json
    All the provenance details associated with this entity
"""
@app.route('/entities/<id>/provenance', methods = ['GET'])
def get_entity_provenance(id):
    # Token is not required, but if an invalid token provided,
    # we need to tell the client with a 401 error
    validate_token_if_auth_header_exists(request)

    # Use the internal token to query the target entity
    # since public entities don't require user token
    token = get_internal_token()

    # Get the entity dict from cache if exists
    # Otherwise query against uuid-api and neo4j to get the entity dict if the id exists
    entity_dict = query_target_entity(id, token)
    uuid = entity_dict['uuid']
    normalized_entity_type = entity_dict['entity_type']

    # A bit validation to prevent Lab or Collection being queried
    supported_entity_types = ['Donor', 'Sample', 'Dataset']
    if normalized_entity_type not in supported_entity_types:
        bad_request_error(f"Unable to get the provenance for this {normalized_entity_type}, supported entity types: {COMMA_SEPARATOR.join(supported_entity_types)}")

    if normalized_entity_type == 'Dataset':
        # Only published/public datasets don't require token
        if entity_dict['status'].lower() != DATASET_STATUS_PUBLISHED:
            # Token is required and the user must belong to HuBMAP-READ group
            token = get_user_token(request, non_public_access_required = True)
    else:
        # The `data_access_level` of Donor/Sample can only be either 'public' or 'consortium'
        if entity_dict['data_access_level'] == ACCESS_LEVEL_CONSORTIUM:
            token = get_user_token(request, non_public_access_required = True)

    # By now, either the entity is public accessible or the user token has the correct access level
    # Will just proceed to get the provenance information
    # Get the `depth` from query string if present and it's used by neo4j query
    # to set the maximum number of hops in the traversal
    depth = None
    if 'depth' in request.args:
        depth = int(request.args.get('depth'))

    # Convert neo4j json to dict
    neo4j_result = app_neo4j_queries.get_provenance(neo4j_driver_instance, uuid, depth)
    raw_provenance_dict = dict(neo4j_result['json'])

    # Normalize the raw provenance nodes based on the yaml schema
    normalized_provenance_dict = {
        'relationships': raw_provenance_dict['relationships'],
        'nodes': []
    }

    for node_dict in raw_provenance_dict['nodes']:
        # The schema yaml doesn't handle Lab nodes, just leave it as is
        if (node_dict['label'] == 'Entity') and (node_dict['entity_type'] != 'Lab'):
            # Generate trigger data
            # Skip some of the properties that are time-consuming to generate via triggers:
            # director_ancestor for Sample, and direct_ancestors for Dataset
            # Also skip next_revision_uuid and previous_revision_uuid for Dataset to avoid additional
            # checks when the target Dataset is public but the revisions are not public
            properties_to_skip = [
                'direct_ancestors',
                'direct_ancestor',
                'next_revision_uuid',
                'previous_revision_uuid'
            ]

            # We'll need to return all the properties (except the ones to skip from above list)
            # including those generated by `on_read_trigger` to have a complete result
            # The 'on_read_trigger' doesn't really need a token
            complete_entity_dict = schema_manager.get_complete_entity_result(token, node_dict, properties_to_skip)

            # Filter out properties not defined or not to be exposed in the schema yaml
            normalized_entity_dict = schema_manager.normalize_entity_result_for_response(complete_entity_dict)

            # Now the node to be used by provenance is all regulated by the schema
            normalized_provenance_dict['nodes'].append(normalized_entity_dict)
        elif node_dict['label'] == 'Activity':
            # Normalize Activity nodes too
            normalized_activity_dict = schema_manager.normalize_activity_result_for_response(node_dict)
            normalized_provenance_dict['nodes'].append(normalized_activity_dict)
        else:
            # Skip Entity Lab nodes
            normalized_provenance_dict['nodes'].append(node_dict)

    provenance_json = provenance.get_provenance_history(uuid, normalized_provenance_dict)

    # Response with the provenance details
    return Response(response = provenance_json, mimetype = "application/json")


"""
Show all the supported entity types

The gateway treats this endpoint as public accessible

Returns
-------
json
    A list of all the available entity types defined in the schema yaml
"""
@app.route('/entity-types', methods = ['GET'])
def get_entity_types():
    # Token is not required, but if an invalid token provided,
    # we need to tell the client with a 401 error
    validate_token_if_auth_header_exists(request)

    return jsonify(schema_manager.get_all_entity_types())


"""
Retrive all the entity nodes for a given entity type
Result filtering is supported based on query string
For example: /<entity_type>/entities?property=uuid

NOTE: this endpoint is NOT exposed via AWS API Gateway due to performance consideration
It's only used by search-api with making internal calls during index/reindex time bypassing AWS API Gateway

Parameters
----------
entity_type : str
    One of the supported entity types: Dataset, Sample, Donor
    Will handle Collection via API endpoint `/collections`

Returns
-------
json
    All the entity nodes in a list of the target entity type
"""
@app.route('/<entity_type>/entities', methods = ['GET'])
def get_entities_by_type(entity_type):
    final_result = []

    # Normalize user provided entity_type
    normalized_entity_type = schema_manager.normalize_entity_type(entity_type)

    # Validate the normalized_entity_type to ensure it's one of the accepted types
    try:
        schema_manager.validate_normalized_entity_type(normalized_entity_type)
    except schema_errors.InvalidNormalizedEntityTypeException as e:
        bad_request_error("Invalid entity type provided: " + entity_type)

    # Handle Collections retrieval using a different endpoint
    if normalized_entity_type == 'Collection':
        bad_request_error("Please use another API endpoint `/collections` to query collections")

    # Result filtering based on query string
    if bool(request.args):
        property_key = request.args.get('property')

        if property_key is not None:
            result_filtering_accepted_property_keys = ['uuid']

            # Validate the target property
            if property_key not in result_filtering_accepted_property_keys:
                bad_request_error(f"Only the following property keys are supported in the query string: {COMMA_SEPARATOR.join(result_filtering_accepted_property_keys)}")

            # Only return a list of the filtered property value of each entity
            property_list = app_neo4j_queries.get_entities_by_type(neo4j_driver_instance, normalized_entity_type, property_key)

            # Final result
            final_result = property_list
        else:
            bad_request_error("The specified query string is not supported. Use '?property=<key>' to filter the result")
    # Return all the details if no property filtering
    else:
        # Get user token from Authorization header
        # Currently the Gateway requires a token for this endpoint
        user_token = get_user_token(request)

        # Get back a list of entity dicts for the given entity type
        entities_list = app_neo4j_queries.get_entities_by_type(neo4j_driver_instance, normalized_entity_type)

        # We'll return all the properties but skip these time-consuming ones
        # Donor doesn't need to skip any
        # Collection is not handled by this call
        properties_to_skip = [
            # Properties to skip for Sample
            'direct_ancestor',
            # Properties to skip for Upload
            'datasets',
            # Properties to skip for Dataset
            'direct_ancestors',
            'collections',
            'upload',
            'title', 
            'previous_revision_uuid', 
            'next_revision_uuid'
        ]

        complete_entities_list = schema_manager.get_complete_entities_list(user_token, entities_list, properties_to_skip)

        # Final result after normalization
        final_result = schema_manager.normalize_entities_list_for_response(complete_entities_list)

    # Response with the final result
    return jsonify(final_result)


"""
Retrive the collection detail by id

The gateway treats this endpoint as public accessible

An optional Globus groups token can be provided in a standard Authentication Bearer header. If a valid token
is provided with group membership in the HuBMAP-Read group any collection matching the id will be returned.
otherwise if no token is provided or a valid token with no HuBMAP-Read group membership then
only a public collection will be returned.  Public collections are defined as being published via a DOI 
(collection.registered_doi not null) and at least one of the connected datasets is public
(dataset.status == 'Published'). For public collections only connected datasets that are
public are returned with it.

Parameters
----------
id : str
    The HuBMAP ID (e.g. HBM123.ABCD.456) or UUID of target collection 

Returns
-------
json
    The collection detail with a list of connected datasets (only public datasets 
    if user doesn't have the right access permission)
"""
@app.route('/collections/<id>', methods = ['GET'])
def get_collection(id):
    # Token is not required, but if an invalid token provided,
    # we need to tell the client with a 401 error
    validate_token_if_auth_header_exists(request)

    # Use the internal token to query the target collection
    # since public collections don't require user token
    token = get_internal_token()

    # Get the entity dict from cache if exists
    # Otherwise query against uuid-api and neo4j to get the entity dict if the id exists
    collection_dict = query_target_entity(id, token)

    # A bit validation
    if collection_dict['entity_type'] != 'Collection':
        bad_request_error("Target entity of the given id is not a collection")

    # Try to get user token from Authorization header
    # It's highly possible that there's no token provided
    user_token = get_user_token(request)

    # The user_token is flask.Response on error
    # Without token, the user can only access public collections, modify the collection result
    # by only returning public datasets attached to this collection
    if isinstance(user_token, Response):
        # When the requested collection is not public, send back 401
        if ('registered_doi' not in collection_dict) or ('doi_url' not in collection_dict):
            # Require a valid token in this case
            unauthorized_error("The reqeusted collection is not public, a Globus token with the right access permission is required.")

        # Otherwise only return the public datasets attached to this collection
        # for Collection.datasets property
        complete_dict = get_complete_public_collection_dict(collection_dict)
    else:
        # When the groups token is valid, but the user doesn't belong to HuBMAP-READ group
        # Or the token is valid but doesn't contain group information (auth token or transfer token)
        # Only return the public datasets attached to this Collection
        if not user_in_hubmap_read_group(request):
            complete_dict = get_complete_public_collection_dict(collection_dict)
        else:
            # We'll need to return all the properties including those
            # generated by `on_read_trigger` to have a complete result
            complete_dict = schema_manager.get_complete_entity_result(user_token, collection_dict)

    # Will also filter the result based on schema
    normalized_complete_dict = schema_manager.normalize_entity_result_for_response(complete_dict)

    # Response with the final result
    return jsonify(normalized_complete_dict)


"""
Retrive all the public collections

The gateway treats this endpoint as public accessible

Result filtering is supported based on query string
For example: /collections?property=uuid

Only return public collections, for either 
- a valid token in HuBMAP-Read group, 
- a valid token with no HuBMAP-Read group or 
- no token at all

Public collections are defined as being published via a DOI 
(collection.registered_doi is not null) and at least one of the connected datasets is published
(dataset.status == 'Published'). For public collections only connected datasets that are
published are returned with it.

Returns
-------
json
    A list of all the public collection dictionaries (with attached public datasts)
"""
@app.route('/collections', methods = ['GET'])
def get_collections():
    final_result = []

    # Token is not required, but if an invalid token provided,
    # we need to tell the client with a 401 error
    validate_token_if_auth_header_exists(request)

    normalized_entity_type = 'Collection'

    # Result filtering based on query string
    if bool(request.args):
        property_key = request.args.get('property')

        if property_key is not None:
            result_filtering_accepted_property_keys = ['uuid']

            # Validate the target property
            if property_key not in result_filtering_accepted_property_keys:
                bad_request_error(f"Only the following property keys are supported in the query string: {COMMA_SEPARATOR.join(result_filtering_accepted_property_keys)}")

            # Only return a list of the filtered property value of each public collection
            final_result = app_neo4j_queries.get_public_collections(neo4j_driver_instance, property_key)
        else:
            bad_request_error("The specified query string is not supported. Use '?property=<key>' to filter the result")
    # Return all the details if no property filtering
    else:
        # Use the internal token since no user token is requried to access public collections
        token = get_internal_token()

        # Get back a list of public collections dicts
        collections_list = app_neo4j_queries.get_public_collections(neo4j_driver_instance)

        # Modify the Collection.datasets property for each collection dict
        # to contain only public datasets
        for collection_dict in collections_list:
            # Only return the public datasets attached to this collection for Collection.datasets property
            collection_dict = get_complete_public_collection_dict(collection_dict)

        # Generate trigger data and merge into a big dict
        # and skip some of the properties that are time-consuming to generate via triggers
        properties_to_skip = ['datasets']
        complete_collections_list = schema_manager.get_complete_entities_list(token, collections_list, properties_to_skip)

        # Final result after normalization
        final_result = schema_manager.normalize_entities_list_for_response(complete_collections_list)

    # Response with the final result
    return jsonify(final_result)


"""
Create an entity of the target type in neo4j

Response result filtering is supported based on query string
For example: /entities/<entity_type>?return_all_properties=true
Default to skip those time-consuming properties

Parameters
----------
entity_type : str
    One of the target entity types (case-insensitive since will be normalized): Dataset, Donor, Sample, Upload

Returns
-------
json
    All the properties of the newly created entity
"""
@app.route('/entities/<entity_type>', methods = ['POST'])
def create_entity(entity_type):
    # Get user token from Authorization header
    user_token = get_user_token(request)

    # Normalize user provided entity_type
    normalized_entity_type = schema_manager.normalize_entity_type(entity_type)

    # Validate the normalized_entity_type to make sure it's one of the accepted types
    try:
        schema_manager.validate_normalized_entity_type(normalized_entity_type)
    except schema_errors.InvalidNormalizedEntityTypeException as e:
        bad_request_error(f"Invalid entity type provided: {entity_type}")

    # Execute entity level validator defined in schema yaml before entity creation
    # Currently on Dataset and Upload creation require application header
    try:
        schema_manager.execute_entity_level_validator('before_entity_create_validator', normalized_entity_type, request)
    except schema_errors.MissingApplicationHeaderException as e:
        bad_request_error(e)
    except schema_errors.InvalidApplicationHeaderException as e:
        bad_request_error(e)

    # Always expect a json body
    require_json(request)

    # Parse incoming json string into json data(python dict object)
    json_data_dict = request.get_json()

    # Validate request json against the yaml schema
    try:
        schema_manager.validate_json_data_against_schema(json_data_dict, normalized_entity_type)
    except schema_errors.SchemaValidationException as e:
        # No need to log the validation errors
        bad_request_error(str(e))

    # Execute property level validators defined in schema yaml before entity property creation
    # Use empty dict {} to indicate there's no existing_data_dict
    try:
        schema_manager.execute_property_level_validators('before_property_create_validators', normalized_entity_type, request, {}, json_data_dict)
    # Currently only ValueError
    except ValueError as e:
        bad_request_error(e)

    # Sample and Dataset: additional validation, create entity, after_create_trigger
    # Collection and Donor: create entity
    if normalized_entity_type == 'Sample':
        # A bit more validation to ensure if `organ` code is set, the `specimen_type` must be set to "organ"
        # Vise versa, if `specimen_type` is set to "organ", `organ` code is required
        if ('specimen_type' in json_data_dict) and (json_data_dict['specimen_type'].lower() == 'organ'):
            if ('organ' not in json_data_dict) or (json_data_dict['organ'].strip() == ''):
                bad_request_error("A valid organ code is required when the specimen_type is organ")
        else:
            if 'organ' in json_data_dict:
                bad_request_error("The specimen_type must be organ when an organ code is provided")

        # A bit more validation for new sample to be linked to existing source entity
        direct_ancestor_uuid = json_data_dict['direct_ancestor_uuid']
        # Check existence of the direct ancestor (either another Sample or Donor)
        direct_ancestor_dict = query_target_entity(direct_ancestor_uuid, user_token)

        # Creating the ids require organ code to be specified for the samples to be created when the
        # sample's direct ancestor is a Donor.
        # Must be one of the codes from: https://github.com/hubmapconsortium/search-api/blob/test-release/src/search-schema/data/definitions/enums/organ_types.yaml
        if direct_ancestor_dict['entity_type'] == 'Donor':
            # `specimen_type` is required on create
            if json_data_dict['specimen_type'].lower() != 'organ':
                bad_request_error("The specimen_type must be organ since the direct ancestor is a Donor")

            # Currently we don't validate the provided organ code though
            if ('organ' not in json_data_dict) or (json_data_dict['organ'].strip() == ''):
                bad_request_error("A valid organ code is required when the direct ancestor is a Donor")

        # Generate 'before_create_triiger' data and create the entity details in Neo4j
        merged_dict = create_entity_details(request, normalized_entity_type, user_token, json_data_dict)
    elif normalized_entity_type == 'Dataset':
        # `direct_ancestor_uuids` is required for creating new Dataset
        # Check existence of those direct ancestors
        for direct_ancestor_uuid in json_data_dict['direct_ancestor_uuids']:
            direct_ancestor_dict = query_target_entity(direct_ancestor_uuid, user_token)

        # Also check existence of the previous revision dataset if specified
        if 'previous_revision_uuid' in json_data_dict:
            previous_version_dict = query_target_entity(json_data_dict['previous_revision_uuid'], user_token)

            # Make sure the previous version entity is either a Dataset or Sample
            if previous_version_dict['entity_type'] not in ['Dataset', 'Sample']:
                bad_request_error(f"The previous_revision_uuid specified for this dataset must be either a Dataset or Sample")

            # Also need to validate if the given 'previous_revision_uuid' has already had
            # an exisiting next revision
            # Only return a list of the uuids, no need to get back the list of dicts
            next_revisions_list = app_neo4j_queries.get_next_revisions(neo4j_driver_instance, previous_version_dict['uuid'], 'uuid')

            # As long as the list is not empty, tell the users to use a different 'previous_revision_uuid'
            if next_revisions_list:
                bad_request_error(f"The previous_revision_uuid specified for this dataset has already had a next revision")

            # Only published datasets can have revisions made of them. Verify that that status of the Dataset specified
            # by previous_revision_uuid is published. Else, bad request error.
            if previous_version_dict['status'].lower() != DATASET_STATUS_PUBLISHED:
                bad_request_error(f"The previous_revision_uuid specified for this dataset must be 'Published' in order to create a new revision from it")

        # Generate 'before_create_triiger' data and create the entity details in Neo4j
        merged_dict = create_entity_details(request, normalized_entity_type, user_token, json_data_dict)
    else:
        # Generate 'before_create_triiger' data and create the entity details in Neo4j
        merged_dict = create_entity_details(request, normalized_entity_type, user_token, json_data_dict)

    # For Donor: link to parent Lab node
    # For Sample: link to existing direct ancestor
    # For Dataset: link to direct ancestors
    # For Upload: link to parent Lab node
    after_create(normalized_entity_type, user_token, merged_dict)

    # By default we'll return all the properties but skip these time-consuming ones
    # Donor doesn't need to skip any
    properties_to_skip = []

    if normalized_entity_type == 'Sample':
        properties_to_skip = [
            'direct_ancestor'
        ]
    elif normalized_entity_type == 'Dataset':
        properties_to_skip = [
            'direct_ancestors',
            'collections',
            'upload',
            'title', 
            'previous_revision_uuid', 
            'next_revision_uuid'
        ]
    elif normalized_entity_type in ['Upload', 'Collection']:
        properties_to_skip = [
            'datasets'
        ]

    # Result filtering based on query string
    # Will return all properties by running all the read triggers
    # If the reuqest specifies `/entities/<entity_type>?return_all_properties=true`
    if bool(request.args):
        # The parased query string value is a string 'true'
        return_all_properties = request.args.get('return_all_properties')

        if (return_all_properties is not None) and (return_all_properties.lower() == 'true'):
            properties_to_skip = []

    # Generate the filtered or complete entity dict to send back
    complete_dict = schema_manager.get_complete_entity_result(user_token, merged_dict, properties_to_skip)

    # Will also filter the result based on schema
    normalized_complete_dict = schema_manager.normalize_entity_result_for_response(complete_dict)

    # Also index the new entity node in elasticsearch via search-api
    reindex_entity(complete_dict['uuid'], user_token)

    return jsonify(normalized_complete_dict)


"""
Create multiple samples from the same source entity

Parameters
----------
count : str
    The number of samples to be created

Returns
-------
json
    All the properties of the newly created entity
"""
@app.route('/entities/multiple-samples/<count>', methods = ['POST'])
def create_multiple_samples(count):
    # Get user token from Authorization header
    user_token = get_user_token(request)

    # Normalize user provided entity_type
    normalized_entity_type = 'Sample'

    # Always expect a json body
    require_json(request)

    # Parse incoming json string into json data(python dict object)
    json_data_dict = request.get_json()

    # Validate request json against the yaml schema
    try:
        schema_manager.validate_json_data_against_schema(json_data_dict, normalized_entity_type)
    except schema_errors.SchemaValidationException as e:
        # No need to log the validation errors
        bad_request_error(str(e))

    # `direct_ancestor_uuid` is required on create
    # Check existence of the direct ancestor (either another Sample or Donor)
    direct_ancestor_dict = query_target_entity(json_data_dict['direct_ancestor_uuid'], user_token)

    # Creating the ids require organ code to be specified for the samples to be created when the
    # sample's direct ancestor is a Donor.
    # Must be one of the codes from: https://github.com/hubmapconsortium/search-api/blob/test-release/src/search-schema/data/definitions/enums/organ_types.yaml
    if direct_ancestor_dict['entity_type'] == 'Donor':
        # `specimen_type` is required on create
        if json_data_dict['specimen_type'].lower() != 'organ':
            bad_request_error("The specimen_type must be organ since the direct ancestor is a Donor")

        # Currently we don't validate the provided organ code though
        if ('organ' not in json_data_dict) or (not json_data_dict['organ']):
            bad_request_error("A valid organ code is required since the direct ancestor is a Donor")

    # Generate 'before_create_triiger' data and create the entity details in Neo4j
    generated_ids_dict_list = create_multiple_samples_details(request, normalized_entity_type, user_token, json_data_dict, count)

    # Also index the each new Sample node in elasticsearch via search-api
    for id_dict in generated_ids_dict_list:
        reindex_entity(id_dict['uuid'], user_token)

    return jsonify(generated_ids_dict_list)


"""
Update the properties of a given entity

Response result filtering is supported based on query string
For example: /entities/<id>?return_all_properties=true
Default to skip those time-consuming properties

Parameters
----------
entity_type : str
    One of the normalized entity types: Dataset, Collection, Sample, Donor
id : str
    The HuBMAP ID (e.g. HBM123.ABCD.456) or UUID of target entity 

Returns
-------
json
    All the updated properties of the target entity
"""
@app.route('/entities/<id>', methods = ['PUT'])
def update_entity(id):
    # Get user token from Authorization header
    user_token = get_user_token(request)

    # Always expect a json body
    require_json(request)

    # Parse incoming json string into json data(python dict object)
    json_data_dict = request.get_json()

    # Normalize user provided status
    if "status" in json_data_dict:
        normalized_status = schema_manager.normalize_status(json_data_dict["status"])
        json_data_dict["status"] = normalized_status

    # Normalize user provided status
    if "sub_status" in json_data_dict:
        normalized_status = schema_manager.normalize_status(json_data_dict["sub_status"])
        json_data_dict["sub_status"] = normalized_status

    # Get the entity dict from cache if exists
    # Otherwise query against uuid-api and neo4j to get the entity dict if the id exists
    entity_dict = query_target_entity(id, user_token)

    # Normalize user provided entity_type
    normalized_entity_type = schema_manager.normalize_entity_type(entity_dict['entity_type'])

    # Note, we don't support entity level validators on entity update via PUT
    # Only entity create via POST is supported at the entity level

    # Validate request json against the yaml schema
    # Pass in the entity_dict for missing required key check, this is different from creating new entity
    try:
        schema_manager.validate_json_data_against_schema(json_data_dict, normalized_entity_type, existing_entity_dict = entity_dict)
    except schema_errors.SchemaValidationException as e:
        # No need to log the validation errors
        bad_request_error(str(e))

    # Execute property level validators defined in schema yaml before entity property update
    try:
        schema_manager.execute_property_level_validators('before_property_update_validators', normalized_entity_type, request, entity_dict, json_data_dict)
    except (schema_errors.MissingApplicationHeaderException,
            schema_errors.InvalidApplicationHeaderException,
            KeyError,
            ValueError) as e:
        bad_request_error(e)

    # Sample, Dataset, and Upload: additional validation, update entity, after_update_trigger
    # Collection and Donor: update entity
    if normalized_entity_type == 'Sample':
        # A bit more validation for updating the sample and the linkage to existing source entity
        has_direct_ancestor_uuid = False
        if ('direct_ancestor_uuid' in json_data_dict) and json_data_dict['direct_ancestor_uuid']:
            has_direct_ancestor_uuid = True

            direct_ancestor_uuid = json_data_dict['direct_ancestor_uuid']
            # Check existence of the source entity
            direct_ancestor_dict = query_target_entity(direct_ancestor_uuid, user_token)
            # Also make sure it's either another Sample or a Donor
            if direct_ancestor_dict['entity_type'] not in ['Donor', 'Sample']:
                bad_request_error(f"The uuid: {direct_ancestor_uuid} is not a Donor neither a Sample, cannot be used as the direct ancestor of this Sample")

        # Generate 'before_update_triiger' data and update the entity details in Neo4j
        merged_updated_dict = update_entity_details(request, normalized_entity_type, user_token, json_data_dict, entity_dict)

        # Handle linkages update via `after_update_trigger` methods
        if has_direct_ancestor_uuid:
            after_update(normalized_entity_type, user_token, merged_updated_dict)
    elif normalized_entity_type == 'Dataset':
        # A bit more validation if `direct_ancestor_uuids` provided
        has_direct_ancestor_uuids = False
        if ('direct_ancestor_uuids' in json_data_dict) and (json_data_dict['direct_ancestor_uuids']):
            has_direct_ancestor_uuids = True

            # Check existence of those source entities
            for direct_ancestor_uuid in json_data_dict['direct_ancestor_uuids']:
                direct_ancestor_dict = query_target_entity(direct_ancestor_uuid, user_token)

        # Generate 'before_update_trigger' data and update the entity details in Neo4j
        merged_updated_dict = update_entity_details(request, normalized_entity_type, user_token, json_data_dict, entity_dict)

        # Handle linkages update via `after_update_trigger` methods
        if has_direct_ancestor_uuids:
            after_update(normalized_entity_type, user_token, merged_updated_dict)
    elif normalized_entity_type == 'Upload':
        has_dataset_uuids_to_link = False
        if ('dataset_uuids_to_link' in json_data_dict) and (json_data_dict['dataset_uuids_to_link']):
            has_dataset_uuids_to_link = True

            # Check existence of those datasets to be linked
            # If one of the datasets to be linked appears to be already linked,
            # neo4j query won't create the new linkage due to the use of `MERGE`
            for dataset_uuid in json_data_dict['dataset_uuids_to_link']:
                dataset_dict = query_target_entity(dataset_uuid, user_token)
                # Also make sure it's a Dataset
                if dataset_dict['entity_type'] != 'Dataset':
                    bad_request_error(f"The uuid: {dataset_uuid} is not a Dataset, cannot be linked to this Upload")

        has_dataset_uuids_to_unlink = False
        if ('dataset_uuids_to_unlink' in json_data_dict) and (json_data_dict['dataset_uuids_to_unlink']):
            has_dataset_uuids_to_unlink = True

            # Check existence of those datasets to be unlinked
            # If one of the datasets to be unlinked appears to be not linked at all,
            # the neo4j cypher will simply skip it because it won't match the "MATCH" clause
            # So no need to tell the end users that this dataset is not linked
            # Let alone checking the entity type to ensure it's a Dataset
            for dataset_uuid in json_data_dict['dataset_uuids_to_unlink']:
                dataset_dict = query_target_entity(dataset_uuid, user_token)

        # Generate 'before_update_trigger' data and update the entity details in Neo4j
        merged_updated_dict = update_entity_details(request, normalized_entity_type, user_token, json_data_dict, entity_dict)

        # Handle linkages update via `after_update_trigger` methods
        if has_dataset_uuids_to_link or has_dataset_uuids_to_unlink:
            after_update(normalized_entity_type, user_token, merged_updated_dict)
    else:
        # Generate 'before_update_triiger' data and update the entity details in Neo4j
        merged_updated_dict = update_entity_details(request, normalized_entity_type, user_token, json_data_dict, entity_dict)

    # By default we'll return all the properties but skip these time-consuming ones
    # Donor doesn't need to skip any
    properties_to_skip = []

    if normalized_entity_type == 'Sample':
        properties_to_skip = [
            'direct_ancestor'
        ]
    elif normalized_entity_type == 'Dataset':
        properties_to_skip = [
            'direct_ancestors',
            'collections',
            'upload',
            'title', 
            'previous_revision_uuid', 
            'next_revision_uuid'
        ]
    elif normalized_entity_type in ['Upload', 'Collection']:
        properties_to_skip = [
            'datasets'
        ]

    # Result filtering based on query string
    # Will return all properties by running all the read triggers
    # If the reuqest specifies `/entities/<id>?return_all_properties=true`
    if bool(request.args):
        # The parased query string value is a string 'true'
        return_all_properties = request.args.get('return_all_properties')

        if (return_all_properties is not None) and (return_all_properties.lower() == 'true'):
            properties_to_skip = []

    # Generate the filtered or complete entity dict to send back
    complete_dict = schema_manager.get_complete_entity_result(user_token, merged_updated_dict, properties_to_skip)

    # Will also filter the result based on schema
    normalized_complete_dict = schema_manager.normalize_entity_result_for_response(complete_dict)

    # Remove the old entity from cache
    # DO NOT update the cache with new entity dict because the returned dict from PUT (some properties maybe skipped)
    # can be different from the one generated by GET call 
    entity_cache.pop(id, None)

    # Also reindex the updated entity node in elasticsearch via search-api
    reindex_entity(entity_dict['uuid'], user_token)

    return jsonify(normalized_complete_dict)


"""
Get all ancestors of the given entity

The gateway treats this endpoint as public accessible

Result filtering based on query string
For example: /ancestors/<id>?property=uuid

Parameters
----------
id : str
    The HuBMAP ID (e.g. HBM123.ABCD.456) or UUID of given entity 

Returns
-------
json
    A list of all the ancestors of the target entity
"""
@app.route('/ancestors/<id>', methods = ['GET'])
def get_ancestors(id):
    final_result = []

    # Token is not required, but if an invalid token provided,
    # we need to tell the client with a 401 error
    validate_token_if_auth_header_exists(request)

    # Use the internal token to query the target entity
    # since public entities don't require user token
    token = get_internal_token()

    # Get the entity dict from cache if exists
    # Otherwise query against uuid-api and neo4j to get the entity dict if the id exists
    entity_dict = query_target_entity(id, token)
    normalized_entity_type = entity_dict['entity_type']
    uuid = entity_dict['uuid']

    # Collection doesn't have ancestors via Activity nodes
    if normalized_entity_type == 'Collection':
        bad_request_error(f"Unsupported entity type of id {id}: {normalized_entity_type}")

    if normalized_entity_type == 'Dataset':
        # Only published/public datasets don't require token
        if entity_dict['status'].lower() != DATASET_STATUS_PUBLISHED:
            # Token is required and the user must belong to HuBMAP-READ group
            token = get_user_token(request, non_public_access_required = True)
    elif normalized_entity_type == 'Sample':
        # The `data_access_level` of Sample can only be either 'public' or 'consortium'
        if entity_dict['data_access_level'] == ACCESS_LEVEL_CONSORTIUM:
            token = get_user_token(request, non_public_access_required = True)
    else:
        # Donor and Upload will always get back an empty list
        # becuase their direct ancestor is Lab, which is being skipped by Neo4j query
        # So no need to execute the code below
        return jsonify(final_result)

    # By now, either the entity is public accessible or the user token has the correct access level
    # Result filtering based on query string
    if bool(request.args):
        property_key = request.args.get('property')

        if property_key is not None:
            result_filtering_accepted_property_keys = ['uuid']

            # Validate the target property
            if property_key not in result_filtering_accepted_property_keys:
                bad_request_error(f"Only the following property keys are supported in the query string: {COMMA_SEPARATOR.join(result_filtering_accepted_property_keys)}")

            # Only return a list of the filtered property value of each entity
            property_list = app_neo4j_queries.get_ancestors(neo4j_driver_instance, uuid, property_key)

            # Final result
            final_result = property_list
        else:
            bad_request_error("The specified query string is not supported. Use '?property=<key>' to filter the result")
    # Return all the details if no property filtering
    else:
        ancestors_list = app_neo4j_queries.get_ancestors(neo4j_driver_instance, uuid)

        # Generate trigger data
        # Skip some of the properties that are time-consuming to generate via triggers
        # Also skip next_revision_uuid and previous_revision_uuid for Dataset to avoid additional
        # checks when the target Dataset is public but the revisions are not public
        properties_to_skip = [
            # Properties to skip for Sample
            'direct_ancestor',
            # Properties to skip for Dataset
            'direct_ancestors',
            'collections',
            'upload',
            'title',
            'next_revision_uuid',
            'previous_revision_uuid'
        ]

        complete_entities_list = schema_manager.get_complete_entities_list(token, ancestors_list, properties_to_skip)

        # Final result after normalization
        final_result = schema_manager.normalize_entities_list_for_response(complete_entities_list)

    return jsonify(final_result)


"""
Get all descendants of the given entity
Result filtering based on query string
For example: /descendants/<id>?property=uuid

Parameters
----------
id : str
    The HuBMAP ID (e.g. HBM123.ABCD.456) or UUID of given entity

Returns
-------
json
    A list of all the descendants of the target entity
"""
@app.route('/descendants/<id>', methods = ['GET'])
def get_descendants(id):
    final_result = []

    # Get user token from Authorization header
    user_token = get_user_token(request)

    # Get the entity dict from cache if exists
    # Otherwise query against uuid-api and neo4j to get the entity dict if the id exists
    entity_dict = query_target_entity(id, user_token)
    uuid = entity_dict['uuid']

    # Collection and Upload don't have descendants via Activity nodes
    # No need to check, it'll always return empty list

    # Result filtering based on query string
    if bool(request.args):
        property_key = request.args.get('property')

        if property_key is not None:
            result_filtering_accepted_property_keys = ['uuid']

            # Validate the target property
            if property_key not in result_filtering_accepted_property_keys:
                bad_request_error(f"Only the following property keys are supported in the query string: {COMMA_SEPARATOR.join(result_filtering_accepted_property_keys)}")

            # Only return a list of the filtered property value of each entity
            property_list = app_neo4j_queries.get_descendants(neo4j_driver_instance, uuid, property_key)

            # Final result
            final_result = property_list
        else:
            bad_request_error("The specified query string is not supported. Use '?property=<key>' to filter the result")
    # Return all the details if no property filtering
    else:
        descendants_list = app_neo4j_queries.get_descendants(neo4j_driver_instance, uuid)

        # Generate trigger data and merge into a big dict
        # and skip some of the properties that are time-consuming to generate via triggers
        properties_to_skip = [
            # Properties to skip for Sample
            'direct_ancestor',
            # Properties to skip for Dataset
            'direct_ancestors',
            'collections',
            'upload',
            'title',
            'next_revision_uuid',
            'previous_revision_uuid'
        ]

        complete_entities_list = schema_manager.get_complete_entities_list(user_token, descendants_list, properties_to_skip)

        # Final result after normalization
        final_result = schema_manager.normalize_entities_list_for_response(complete_entities_list)

    return jsonify(final_result)


"""
Get all parents of the given entity

The gateway treats this endpoint as public accessible

Result filtering based on query string
For example: /parents/<id>?property=uuid

Parameters
----------
id : str
    The HuBMAP ID (e.g. HBM123.ABCD.456) or UUID of given entity

Returns
-------
json
    A list of all the parents of the target entity
"""
@app.route('/parents/<id>', methods = ['GET'])
def get_parents(id):
    final_result = []

    # Token is not required, but if an invalid token provided,
    # we need to tell the client with a 401 error
    validate_token_if_auth_header_exists(request)

    # Use the internal token to query the target entity
    # since public entities don't require user token
    token = get_internal_token()

    # Get the entity dict from cache if exists
    # Otherwise query against uuid-api and neo4j to get the entity dict if the id exists
    entity_dict = query_target_entity(id, token)
    normalized_entity_type = entity_dict['entity_type']
    uuid = entity_dict['uuid']

    # Collection doesn't have ancestors via Activity nodes
    if normalized_entity_type == 'Collection':
        bad_request_error(f"Unsupported entity type of id {id}: {normalized_entity_type}")

    if normalized_entity_type == 'Dataset':
        # Only published/public datasets don't require token
        if entity_dict['status'].lower() != DATASET_STATUS_PUBLISHED:
            # Token is required and the user must belong to HuBMAP-READ group
            token = get_user_token(request, non_public_access_required = True)
    elif normalized_entity_type == 'Sample':
        # The `data_access_level` of Sample can only be either 'public' or 'consortium'
        if entity_dict['data_access_level'] == ACCESS_LEVEL_CONSORTIUM:
            token = get_user_token(request, non_public_access_required = True)
    else:
        # Donor and Upload will always get back an empty list
        # becuase their direct ancestor is Lab, which is being skipped by Neo4j query
        # So no need to execute the code below
        return jsonify(final_result)

    # By now, either the entity is public accessible or the user token has the correct access level
    # Result filtering based on query string
    if bool(request.args):
        property_key = request.args.get('property')

        if property_key is not None:
            result_filtering_accepted_property_keys = ['uuid']

            # Validate the target property
            if property_key not in result_filtering_accepted_property_keys:
                bad_request_error(f"Only the following property keys are supported in the query string: {COMMA_SEPARATOR.join(result_filtering_accepted_property_keys)}")

            # Only return a list of the filtered property value of each entity
            property_list = app_neo4j_queries.get_parents(neo4j_driver_instance, uuid, property_key)

            # Final result
            final_result = property_list
        else:
            bad_request_error("The specified query string is not supported. Use '?property=<key>' to filter the result")
    # Return all the details if no property filtering
    else:
        parents_list = app_neo4j_queries.get_parents(neo4j_driver_instance, uuid)

        # Generate trigger data
        # Skip some of the properties that are time-consuming to generate via triggers
        # Also skip next_revision_uuid and previous_revision_uuid for Dataset to avoid additional
        # checks when the target Dataset is public but the revisions are not public
        properties_to_skip = [
            # Properties to skip for Sample
            'direct_ancestor',
            # Properties to skip for Dataset
            'direct_ancestors',
            'collections',
            'upload',
            'title',
            'next_revision_uuid',
            'previous_revision_uuid'
        ]

        complete_entities_list = schema_manager.get_complete_entities_list(token, parents_list, properties_to_skip)

        # Final result after normalization
        final_result = schema_manager.normalize_entities_list_for_response(complete_entities_list)

    return jsonify(final_result)


"""
Get all chilren of the given entity
Result filtering based on query string
For example: /children/<id>?property=uuid

Parameters
----------
id : str
    The HuBMAP ID (e.g. HBM123.ABCD.456) or UUID of given entity

Returns
-------
json
    A list of all the children of the target entity
"""
@app.route('/children/<id>', methods = ['GET'])
def get_children(id):
    final_result = []

    # Get user token from Authorization header
    user_token = get_user_token(request)

    # Get the entity dict from cache if exists
    # Otherwise query against uuid-api and neo4j to get the entity dict if the id exists
    entity_dict = query_target_entity(id, user_token)
    uuid = entity_dict['uuid']

    # Collection and Upload don't have children via Activity nodes
    # No need to check, it'll always return empty list

    # Result filtering based on query string
    if bool(request.args):
        property_key = request.args.get('property')

        if property_key is not None:
            result_filtering_accepted_property_keys = ['uuid']

            # Validate the target property
            if property_key not in result_filtering_accepted_property_keys:
                bad_request_error(f"Only the following property keys are supported in the query string: {COMMA_SEPARATOR.join(result_filtering_accepted_property_keys)}")

            # Only return a list of the filtered property value of each entity
            property_list = app_neo4j_queries.get_children(neo4j_driver_instance, uuid, property_key)

            # Final result
            final_result = property_list
        else:
            bad_request_error("The specified query string is not supported. Use '?property=<key>' to filter the result")
    # Return all the details if no property filtering
    else:
        children_list = app_neo4j_queries.get_children(neo4j_driver_instance, uuid)

        # Generate trigger data and merge into a big dict
        # and skip some of the properties that are time-consuming to generate via triggers
        properties_to_skip = [
            # Properties to skip for Sample
            'direct_ancestor',
            # Properties to skip for Dataset
            'direct_ancestors',
            'collections',
            'upload',
            'title',
            'next_revision_uuid',
            'previous_revision_uuid'
        ]

        complete_entities_list = schema_manager.get_complete_entities_list(user_token, children_list, properties_to_skip)

        # Final result after normalization
        final_result = schema_manager.normalize_entities_list_for_response(complete_entities_list)

    return jsonify(final_result)


"""
Get all previous revisions of the given entity
Result filtering based on query string
For example: /previous_revisions/<id>?property=uuid

Parameters
----------
id : str
    The HuBMAP ID (e.g. HBM123.ABCD.456) or UUID of given entity

Returns
-------
json
    A list of entities that are the previous revisions of the target entity
"""
@app.route('/previous_revisions/<id>', methods = ['GET'])
def get_previous_revisions(id):
    # Get user token from Authorization header
    user_token = get_user_token(request)

    # Get the entity dict from cache if exists
    # Otherwise query against uuid-api and neo4j to get the entity dict if the id exists
    entity_dict = query_target_entity(id, user_token)
    uuid = entity_dict['uuid']

    # Result filtering based on query string
    if bool(request.args):
        property_key = request.args.get('property')

        if property_key is not None:
            result_filtering_accepted_property_keys = ['uuid']

            # Validate the target property
            if property_key not in result_filtering_accepted_property_keys:
                bad_request_error(f"Only the following property keys are supported in the query string: {COMMA_SEPARATOR.join(result_filtering_accepted_property_keys)}")

            # Only return a list of the filtered property value of each entity
            property_list = app_neo4j_queries.get_previous_revisions(neo4j_driver_instance, uuid, property_key)

            # Final result
            final_result = property_list
        else:
            bad_request_error("The specified query string is not supported. Use '?property=<key>' to filter the result")
    # Return all the details if no property filtering
    else:
        descendants_list = app_neo4j_queries.get_previous_revisions(neo4j_driver_instance, uuid)

        # Generate trigger data and merge into a big dict
        # and skip some of the properties that are time-consuming to generate via triggers
        properties_to_skip = [
            'collections', 
            'upload', 
            'title',
            'direct_ancestors'
        ]

        complete_entities_list = schema_manager.get_complete_entities_list(user_token, descendants_list, properties_to_skip)

        # Final result after normalization
        final_result = schema_manager.normalize_entities_list_for_response(complete_entities_list)

    return jsonify(final_result)


"""
Get all next revisions of the given entity
Result filtering based on query string
For example: /next_revisions/<id>?property=uuid

Parameters
----------
id : str
    The HuBMAP ID (e.g. HBM123.ABCD.456) or UUID of given entity

Returns
-------
json
    A list of entities that are the next revisions of the target entity
"""
@app.route('/next_revisions/<id>', methods = ['GET'])
def get_next_revisions(id):
    # Get user token from Authorization header
    user_token = get_user_token(request)

    # Get the entity dict from cache if exists
    # Otherwise query against uuid-api and neo4j to get the entity dict if the id exists
    entity_dict = query_target_entity(id, user_token)
    uuid = entity_dict['uuid']

    # Result filtering based on query string
    if bool(request.args):
        property_key = request.args.get('property')

        if property_key is not None:
            result_filtering_accepted_property_keys = ['uuid']

            # Validate the target property
            if property_key not in result_filtering_accepted_property_keys:
                bad_request_error(f"Only the following property keys are supported in the query string: {COMMA_SEPARATOR.join(result_filtering_accepted_property_keys)}")

            # Only return a list of the filtered property value of each entity
            property_list = app_neo4j_queries.get_next_revisions(neo4j_driver_instance, uuid, property_key)

            # Final result
            final_result = property_list
        else:
            bad_request_error("The specified query string is not supported. Use '?property=<key>' to filter the result")
    # Return all the details if no property filtering
    else:
        descendants_list = app_neo4j_queries.get_next_revisions(neo4j_driver_instance, uuid)

        # Generate trigger data and merge into a big dict
        # and skip some of the properties that are time-consuming to generate via triggers
        properties_to_skip = [
            'collections', 
            'upload', 
            'title',
            'direct_ancestors'
        ]

        complete_entities_list = schema_manager.get_complete_entities_list(user_token, descendants_list, properties_to_skip)

        # Final result after normalization
        final_result = schema_manager.normalize_entities_list_for_response(complete_entities_list)

    return jsonify(final_result)



"""
Link the given list of datasets to the target collection

JSON request body example:
{
    "dataset_uuids": [
        "fb6757b606ac35be7fa85062fde9c2e1",
        "81a9fa68b2b4ea3e5f7cb17554149473",
        "3ac0768d61c6c84f0ec59d766e123e05",
        "0576b972e074074b4c51a61c3d17a6e3"
    ]
}

Parameters
----------
collection_uuid : str
    The UUID of target collection 

Returns
-------
json
    JSON string containing a success message with 200 status code
"""
@app.route('/collections/<collection_uuid>/add-datasets', methods = ['PUT'])
def add_datasets_to_collection(collection_uuid):
    # Get user token from Authorization header
    user_token = get_user_token(request)

    # Query target entity against uuid-api and neo4j and return as a dict if exists
    entity_dict = query_target_entity(collection_uuid, user_token)
    if entity_dict['entity_type'] != 'Collection':
        bad_request_error(f"The UUID provided in URL is not a Collection: {collection_uuid}")

    # Always expect a json body
    require_json(request)

    # Parse incoming json string into json data(python list object)
    json_data_dict = request.get_json()

    if 'dataset_uuids' not in json_data_dict:
        bad_request_error("Missing 'dataset_uuids' key in the request JSON.")

    if not json_data_dict['dataset_uuids']:
        bad_request_error("JSON field 'dataset_uuids' can not be empty list.")

    # Now we have a list of uuids
    dataset_uuids_list = json_data_dict['dataset_uuids']

    # Make sure all the given uuids are datasets
    for dataset_uuid in dataset_uuids_list:
        entity_dict = query_target_entity(dataset_uuid, user_token)
        if entity_dict['entity_type'] != 'Dataset':
            bad_request_error(f"The UUID provided in JSON is not a Dataset: {dataset_uuid}")

    try:
        app_neo4j_queries.add_datasets_to_collection(neo4j_driver_instance, collection_uuid, dataset_uuids_list)
    except TransactionError:
        msg = "Failed to create the linkage between the given datasets and the target collection"
        # Log the full stack trace, prepend a line with our message
        logger.exception(msg)
        # Terminate and let the users know
        internal_server_error(msg)

    # Send response with success message
    return jsonify(message = "Successfully added all the specified datasets to the target collection")


"""
Redirect a request from a doi service for a dataset or collection

The gateway treats this endpoint as public accessible

Parameters
----------
id : str
    The HuBMAP ID (e.g. HBM123.ABCD.456) or UUID of the target entity
"""
# To continue supporting the already published collection DOIs
@app.route('/collection/redirect/<id>', methods = ['GET'])
# New route
@app.route('/doi/redirect/<id>', methods = ['GET'])
def doi_redirect(id):
    # Use the internal token to query the target entity
    # since public entities don't require user token
    token = get_internal_token()

    # Query target entity against uuid-api and neo4j and return as a dict if exists
    entity_dict = query_target_entity(id, token)

    entity_type = entity_dict['entity_type']

    # Only for collection
    if entity_type not in ['Collection', 'Dataset']:
        bad_request_error("The target entity of the specified id must be a Collection or Dataset")

    uuid = entity_dict['uuid']

    # URL template
    redirect_url = app.config['DOI_REDIRECT_URL']

    if (redirect_url.lower().find('<entity_type>') == -1) or (redirect_url.lower().find('<identifier>') == -1):
        # Log the full stack trace, prepend a line with our message
        msg = "Incorrect configuration value for 'DOI_REDIRECT_URL'"
        logger.exception(msg)
        internal_server_error(msg)

    rep_entity_type_pattern = re.compile(re.escape('<entity_type>'), re.RegexFlag.IGNORECASE)
    redirect_url = rep_entity_type_pattern.sub(entity_type.lower(), redirect_url)

    rep_identifier_pattern = re.compile(re.escape('<identifier>'), re.RegexFlag.IGNORECASE)
    redirect_url = rep_identifier_pattern.sub(uuid, redirect_url)

    resp = Response("Page has moved", 307)
    resp.headers['Location'] = redirect_url

    return resp


"""
Redirection method created for REFERENCE organ DOI redirection, but can be for others if needed

The gateway treats this endpoint as public accessible

Parameters
----------
hmid : str
    The HuBMAP ID (e.g. HBM123.ABCD.456)
"""
@app.route('/redirect/<hmid>', methods = ['GET'])
def redirect(hmid):
    cid = hmid.upper().strip()
    if cid in reference_redirects:
        redir_url = reference_redirects[cid]
        resp = Response("page has moved", 307)
        resp.headers['Location'] = redir_url
        return resp
    else:
        return Response(f"{hmid} not found.", 404)

"""
Get the Globus URL to the given Dataset or Upload

The gateway treats this endpoint as public accessible

It will provide a Globus URL to the dataset/upload directory in of three Globus endpoints based on the access
level of the user (public, consortium or protected), public only, of course, if no token is provided.
If a dataset/upload isn't found a 404 will be returned. There is a chance that a 500 can be returned, but not
likely under normal circumstances, only for a misconfigured or failing in some way endpoint. 

If the Auth token is provided but is expired or invalid a 401 is returned. If access to the dataset/upload 
is not allowed for the user (or lack of user) a 403 is returned.

Parameters
----------
id : str
    The HuBMAP ID (e.g. HBM123.ABCD.456) or UUID of given entity

Returns
-------
Response
    200 with the Globus Application URL to the directory of dataset/upload
    404 Dataset/Upload not found
    403 Access Forbidden
    401 Unauthorized (bad or expired token)
    500 Unexpected server or other error
"""
# Thd old routes for backward compatibility - will be deprecated eventually
@app.route('/entities/dataset/globus-url/<id>', methods = ['GET'])
@app.route('/dataset/globus-url/<id>', methods = ['GET'])
# New route
@app.route('/entities/<id>/globus-url', methods = ['GET'])
def get_globus_url(id):
    # Token is not required, but if an invalid token provided,
    # we need to tell the client with a 401 error
    validate_token_if_auth_header_exists(request)

    # Use the internal token to query the target entity
    # since public entities don't require user token
    token = get_internal_token()

    # Query target entity against uuid-api and neo4j and return as a dict if exists
    # Then retrieve the allowable data access level (public, protected or consortium)
    # for the dataset and HuBMAP Component ID that the dataset belongs to
    entity_dict = query_target_entity(id, token)
    uuid = entity_dict['uuid']
    normalized_entity_type = entity_dict['entity_type']

    # Only for Dataset and Upload
    if normalized_entity_type not in ['Dataset', 'Upload']:
        bad_request_error("The target entity of the specified id is not a Dataset nor a Upload")

    # Upload doesn't have this 'data_access_level' property, we treat it as 'protected'
    # For Dataset, if no access level is present, default to protected too
    if not 'data_access_level' in entity_dict or string_helper.isBlank(entity_dict['data_access_level']):
        entity_data_access_level = ACCESS_LEVEL_PROTECTED
    else:
        entity_data_access_level = entity_dict['data_access_level']

    # Get the globus groups info based on the groups json file in commons package
    globus_groups_info = globus_groups.get_globus_groups_info()
    groups_by_id_dict = globus_groups_info['by_id']

    if not 'group_uuid' in entity_dict or string_helper.isBlank(entity_dict['group_uuid']):
        msg = f"The 'group_uuid' property is not set for {normalized_entity_type} with uuid: {uuid}"
        logger.exception(msg)
        internal_server_error(msg)

    group_uuid = entity_dict['group_uuid']

    # Validate the group_uuid
    try:
        schema_manager.validate_entity_group_uuid(group_uuid)
    except schema_errors.NoDataProviderGroupException:
        msg = f"Invalid 'group_uuid': {group_uuid} for {normalized_entity_type} with uuid: {uuid}"
        logger.exception(msg)
        internal_server_error(msg)

    group_name = groups_by_id_dict[group_uuid]['displayname']

    try:
        # Get user data_access_level based on token if provided
        # If no Authorization header, default user_info['data_access_level'] == 'public'
        # The user_info contains HIGHEST access level of the user based on the token
        # This call raises an HTTPException with a 401 if any auth issues encountered
        user_info = auth_helper_instance.getUserDataAccessLevel(request)
    # If returns HTTPException with a 401, expired/invalid token
    except HTTPException:
        unauthorized_error("The provided token is invalid or expired")

    # The user is in the Globus group with full access to thie dataset,
    # so they have protected level access to it
    if ('hmgroupids' in user_info) and (group_uuid in user_info['hmgroupids']):
        user_data_access_level = ACCESS_LEVEL_PROTECTED
    else:
        if not 'data_access_level' in user_info:
            msg = f"Unexpected error, data access level could not be found for user trying to access {normalized_entity_type} id: {id}"
            logger.exception(msg)
            return internal_server_error(msg)

        user_data_access_level = user_info['data_access_level'].lower()

    #construct the Globus URL based on the highest level of access that the user has
    #and the level of access allowed for the dataset
    #the first "if" checks to see if the user is a member of the Consortium group
    #that allows all access to this dataset, if so send them to the "protected"
    #endpoint even if the user doesn't have full access to all protected data
    globus_server_uuid = None
    dir_path = ''

    # Note: `entity_data_access_level` for Upload is always default to 'protected'
    # public access
    if entity_data_access_level == ACCESS_LEVEL_PUBLIC:
        globus_server_uuid = app.config['GLOBUS_PUBLIC_ENDPOINT_UUID']
        access_dir = access_level_prefix_dir(app.config['PUBLIC_DATA_SUBDIR'])
        dir_path = dir_path +  access_dir + "/"
    # consortium access
    elif (entity_data_access_level == ACCESS_LEVEL_CONSORTIUM) and (not user_data_access_level == ACCESS_LEVEL_PUBLIC):
        globus_server_uuid = app.config['GLOBUS_CONSORTIUM_ENDPOINT_UUID']
        access_dir = access_level_prefix_dir(app.config['CONSORTIUM_DATA_SUBDIR'])
        dir_path = dir_path + access_dir + group_name + "/"
    # protected access
    elif (entity_data_access_level == ACCESS_LEVEL_PROTECTED) and (user_data_access_level == ACCESS_LEVEL_PROTECTED):
        globus_server_uuid = app.config['GLOBUS_PROTECTED_ENDPOINT_UUID']
        access_dir = access_level_prefix_dir(app.config['PROTECTED_DATA_SUBDIR'])
        dir_path = dir_path + access_dir + group_name + "/"

    if globus_server_uuid is None:
        forbidden_error("Access not granted")

    dir_path = dir_path + uuid + "/"
    dir_path = urllib.parse.quote(dir_path, safe='')

    #https://app.globus.org/file-manager?origin_id=28bbb03c-a87d-4dd7-a661-7ea2fb6ea631&origin_path=%2FIEC%20Testing%20Group%2F03584b3d0f8b46de1b629f04be156879%2F
    url = hm_file_helper.ensureTrailingSlashURL(app.config['GLOBUS_APP_BASE_URL']) + "file-manager?origin_id=" + globus_server_uuid + "&origin_path=" + dir_path

    return Response(url, 200)


"""
Retrive the latest (newest) revision of a Dataset

Public/Consortium access rules apply - if no token/consortium access then 
must be for a public dataset and the returned Dataset must be the latest public version.

Parameters
----------
id : str
    The HuBMAP ID (e.g. HBM123.ABCD.456) or UUID of target entity 

Returns
-------
json
    The detail of the latest revision dataset if exists
    Otherwise an empty JSON object {}
"""
@app.route('/datasets/<id>/latest-revision', methods = ['GET'])
def get_dataset_latest_revision(id):
    # Token is not required, but if an invalid token provided,
    # we need to tell the client with a 401 error
    validate_token_if_auth_header_exists(request)

    # Use the internal token to query the target entity
    # since public entities don't require user token
    token = get_internal_token()

    # Query target entity against uuid-api and neo4j and return as a dict if exists
    entity_dict = query_target_entity(id, token)
    normalized_entity_type = entity_dict['entity_type']
    uuid = entity_dict['uuid']

    # Only for Dataset
    if normalized_entity_type != 'Dataset':
        bad_request_error("The entity of given id is not a Dataset")

    latest_revision_dict = {}

    # Only published/public datasets don't require token
    if entity_dict['status'].lower() != DATASET_STATUS_PUBLISHED:
        # Token is required and the user must belong to HuBMAP-READ group
        token = get_user_token(request, non_public_access_required = True)

        latest_revision_dict = app_neo4j_queries.get_dataset_latest_revision(neo4j_driver_instance, uuid)
    else:
        # Default to the latest "public" revision dataset
        # when no token or not a valid HuBMAP-Read token
        latest_revision_dict = app_neo4j_queries.get_dataset_latest_revision(neo4j_driver_instance, uuid, public = True)

        # Send back the real latest revision dataset if a valid HuBMAP-Read token presents
        if user_in_hubmap_read_group(request):
            latest_revision_dict = app_neo4j_queries.get_dataset_latest_revision(neo4j_driver_instance, uuid)

    # We'll need to return all the properties including those
    # generated by `on_read_trigger` to have a complete result
    # E.g., the 'previous_revision_uuid'
    # Here we skip the 'next_revision_uuid' property becase when the "public" latest revision dataset
    # is not the real latest revision, we don't want the users to see it
    properties_to_skip = [
        'next_revision_uuid'
    ]

    # On entity retrieval, the 'on_read_trigger' doesn't really need a token
    complete_dict = schema_manager.get_complete_entity_result(token, latest_revision_dict, properties_to_skip)

    # Also normalize the result based on schema
    final_result = schema_manager.normalize_entity_result_for_response(complete_dict)

    # Response with the dict
    return jsonify(final_result)


"""
Retrive the calculated revision number of a Dataset

The calculated revision is number is based on the [:REVISION_OF] relationships 
to the oldest dataset in a revision chain. 
Where the oldest dataset = 1 and each newer version is incremented by one (1, 2, 3 ...)

Public/Consortium access rules apply, if is for a non-public dataset 
and no token or a token without membership in HuBMAP-Read group is sent with the request 
then a 403 response should be returned.

Parameters
----------
id : str
    The HuBMAP ID (e.g. HBM123.ABCD.456) or UUID of target entity 

Returns
-------
int
    The calculated revision number
"""
@app.route('/datasets/<id>/revision', methods = ['GET'])
def get_dataset_revision_number(id):
    # Token is not required, but if an invalid token provided,
    # we need to tell the client with a 401 error
    validate_token_if_auth_header_exists(request)

    # Use the internal token to query the target entity
    # since public entities don't require user token
    token = get_internal_token()

    # Query target entity against uuid-api and neo4j and return as a dict if exists
    entity_dict = query_target_entity(id, token)
    normalized_entity_type = entity_dict['entity_type']

    # Only for Dataset
    if normalized_entity_type != 'Dataset':
        bad_request_error("The entity of given id is not a Dataset")

    # Only published/public datasets don't require token
    if entity_dict['status'].lower() != DATASET_STATUS_PUBLISHED:
        # Token is required and the user must belong to HuBMAP-READ group
        token = get_user_token(request, non_public_access_required = True)

    # By now, either the entity is public accessible or
    # the user token has the correct access level
    revision_number = app_neo4j_queries.get_dataset_revision_number(neo4j_driver_instance, entity_dict['uuid'])

    # Response with the integer
    return jsonify(revision_number)


"""
Retract a published dataset with a retraction reason and sub status

Takes as input a json body with required fields "retracted_reason" and "sub_status".
Authorization handled by gateway. Only token of HuBMAP-Data-Admin group can use this call. 

Technically, the same can be achieved by making a PUT call to the generic entity update endpoint
with using a HuBMAP-Data-Admin group token. But doing this is strongly discouraged because we'll
need to add more validators to ensure when "retracted_reason" is provided, there must be a 
"sub_status" filed and vise versa. So consider this call a special use case of entity update.

Parameters
----------
id : str
    The HuBMAP ID (e.g. HBM123.ABCD.456) or UUID of target dataset 

Returns
-------
dict
    The updated dataset details
"""
@app.route('/datasets/<id>/retract', methods=['PUT'])
def retract_dataset(id):
    # Always expect a json body
    require_json(request)

    # Parse incoming json string into json data(python dict object)
    json_data_dict = request.get_json()

    # Normalize user provided status
    if "sub_status" in json_data_dict:
        normalized_status = schema_manager.normalize_status(json_data_dict["sub_status"])
        json_data_dict["sub_status"] = normalized_status

    # Use beblow application-level validations to avoid complicating schema validators
    # The 'retraction_reason' and `sub_status` are the only required/allowed fields. No other fields allowed.
    # Must enforce this rule otherwise we'll need to run after update triggers if any other fields
    # get passed in (which should be done using the generic entity update call)
    if 'retraction_reason' not in json_data_dict:
        bad_request_error("Missing required field: retraction_reason")

    if 'sub_status' not in json_data_dict:
        bad_request_error("Missing required field: sub_status")

    if len(json_data_dict) > 2:
        bad_request_error("Only retraction_reason and sub_status are allowed fields")

    # Must be a HuBMAP-Data-Admin group token
    token = get_user_token(request)

    # Retrieves the neo4j data for a given entity based on the id supplied.
    # The normalized entity-type from this entity is checked to be a dataset
    # If the entity is not a dataset and the dataset is not published, cannot retract
    entity_dict = query_target_entity(id, token)
    normalized_entity_type = entity_dict['entity_type']

    # A bit more application-level validation
    if normalized_entity_type != 'Dataset':
        bad_request_error("The entity of given id is not a Dataset")

    # Validate request json against the yaml schema
    # The given value of `sub_status` is being validated at this step
    try:
        schema_manager.validate_json_data_against_schema(json_data_dict, normalized_entity_type, existing_entity_dict = entity_dict)
    except schema_errors.SchemaValidationException as e:
        # No need to log the validation errors
        bad_request_error(str(e))

    # Execute property level validators defined in schema yaml before entity property update
    try:
        schema_manager.execute_property_level_validators('before_property_update_validators', normalized_entity_type, request, entity_dict, json_data_dict)
    except (schema_errors.MissingApplicationHeaderException,
            schema_errors.InvalidApplicationHeaderException,
            KeyError,
            ValueError) as e:
        bad_request_error(e)

    # No need to call after_update() afterwards because retraction doesn't call any after_update_trigger methods
    merged_updated_dict = update_entity_details(request, normalized_entity_type, token, json_data_dict, entity_dict)

    complete_dict = schema_manager.get_complete_entity_result(token, merged_updated_dict)

    # Will also filter the result based on schema
    normalized_complete_dict = schema_manager.normalize_entity_result_for_response(complete_dict)

    # Also reindex the updated entity node in elasticsearch via search-api
    reindex_entity(entity_dict['uuid'], token)

    return jsonify(normalized_complete_dict)


"""
Retrieve a list of all revisions of a dataset from the id of any dataset in the chain. 
E.g: If there are 5 revisions, and the id for revision 4 is given, a list of revisions
1-5 will be returned in reverse order (newest first). Non-public access is only required to 
retrieve information on non-published datasets. Output will be a list of dictionaries. Each dictionary
contains the dataset revision number and its uuid. Optionally, the full dataset can be included for each.

By default, only the revision number and uuid is included. To include the full dataset, the query 
parameter "include_dataset" can be given with the value of "true". If this parameter is not included or 
is set to false, the dataset will not be included. For example, to include the full datasets for each revision,
use '/datasets/<id>/revisions?include_dataset=true'. To omit the datasets, either set include_dataset=false, or
simply do not include this parameter. 

Parameters
----------
id : str
    The HuBMAP ID (e.g. HBM123.ABCD.456) or UUID of target dataset 

Returns
-------
list
    The list of revision datasets
"""
@app.route('/entities/<id>/revisions', methods=['GET'])
@app.route('/datasets/<id>/revisions', methods=['GET'])
def get_revisions_list(id):
    # By default, do not return dataset. Only return dataset if return_dataset is true
    show_dataset = False
    if bool(request.args):
        include_dataset = request.args.get('include_dataset')
        if (include_dataset is not None) and (include_dataset.lower() == 'true'):
            show_dataset = True
    # Token is not required, but if an invalid token provided,
    # we need to tell the client with a 401 error
    validate_token_if_auth_header_exists(request)

    # Use the internal token to query the target entity
    # since public entities don't require user token
    token = get_internal_token()

    # Query target entity against uuid-api and neo4j and return as a dict if exists
    entity_dict = query_target_entity(id, token)
    normalized_entity_type = entity_dict['entity_type']

    # Only for Dataset
    if normalized_entity_type != 'Dataset':
        bad_request_error("The entity is not a Dataset. Found entity type:" + normalized_entity_type)

    # Only published/public datasets don't require token
    if entity_dict['status'].lower() != DATASET_STATUS_PUBLISHED:
        # Token is required and the user must belong to HuBMAP-READ group
        token = get_user_token(request, non_public_access_required=True)

    # By now, either the entity is public accessible or
    # the user token has the correct access level
    # Get the all the sorted (DESC based on creation timestamp) revisions
    sorted_revisions_list = app_neo4j_queries.get_sorted_revisions(neo4j_driver_instance, entity_dict['uuid'])

    # Skip some of the properties that are time-consuming to generate via triggers
    properties_to_skip = [
        'direct_ancestors',
        'collections',
        'upload',
        'title'
    ]
    complete_revisions_list = schema_manager.get_complete_entities_list(token, sorted_revisions_list, properties_to_skip)
    normalized_revisions_list = schema_manager.normalize_entities_list_for_response(complete_revisions_list)

    # Only check the very last revision (the first revision dict since normalized_revisions_list is already sorted DESC)
    # to determine if send it back or not
    if not user_in_hubmap_read_group(request):
        latest_revision = normalized_revisions_list[0]

        if latest_revision['status'].lower() != DATASET_STATUS_PUBLISHED:
            normalized_revisions_list.pop(0)

            # Also hide the 'next_revision_uuid' of the second last revision from response
            if 'next_revision_uuid' in normalized_revisions_list[0]:
                normalized_revisions_list[0].pop('next_revision_uuid')

    # Now all we need to do is to compose the result list
    results = []
    revision_number = len(normalized_revisions_list)
    for revision in normalized_revisions_list:
        result = {
            'revision_number': revision_number,
            'uuid': revision['uuid']
        }
        if show_dataset:
            result['dataset'] = revision
        results.append(result)
        revision_number -= 1

    return jsonify(results)


"""
Get all organs associated with a given dataset

The gateway treats this endpoint as public accessible

Parameters
----------
id : str
    The HuBMAP ID (e.g. HBM123.ABCD.456) or UUID of given entity

Returns
-------
json
    a list of all the organs associated with the target dataset
"""
@app.route('/datasets/<id>/organs', methods=['GET'])
def get_associated_organs_from_dataset(id):
    # Token is not required, but if an invalid token provided,
    # we need to tell the client with a 401 error
    validate_token_if_auth_header_exists(request)

    # Use the internal token to query the target entity
    # since public entities don't require user token
    token = get_internal_token()

    # Query target entity against uuid-api and neo4j and return as a dict if exists
    entity_dict = query_target_entity(id, token)
    normalized_entity_type = entity_dict['entity_type']

    # Only for Dataset
    if normalized_entity_type != 'Dataset':
        bad_request_error("The entity of given id is not a Dataset")

    # published/public datasets don't require token
    if entity_dict['status'].lower() != DATASET_STATUS_PUBLISHED:
        # Token is required and the user must belong to HuBMAP-READ group
        token = get_user_token(request, non_public_access_required=True)

    # By now, either the entity is public accessible or
    # the user token has the correct access level
    associated_organs = app_neo4j_queries.get_associated_organs_from_dataset(neo4j_driver_instance, entity_dict['uuid'])

    # If there are zero items in the list associated organs, then there are no associated
    # Organs and a 404 will be returned.
    if len(associated_organs) < 1:
        not_found_error("the dataset does not have any associated organs")

    complete_entities_list = schema_manager.get_complete_entities_list(token, associated_organs)

    # Final result after normalization
    final_result = schema_manager.normalize_entities_list_for_response(complete_entities_list)

    return jsonify(final_result)


"""
Get the complete provenance info for all datasets

Authentication
-------
No token is required, however if a token is given it must be valid or an error will be raised. If no token with HuBMAP
Read Group access is given, only datasets designated as "published" will be returned

Query Parameters
-------
    format : string
        Designates the output format of the returned data. Accepted values are "json" and "tsv". If none provided, by 
        default will return a tsv.
    group_uuid : string
        Filters returned datasets by a given group uuid. 
    organ : string
        Filters returned datasets related to a samples of the given organ. Accepts 2 character organ codes. These codes
        must match the organ types yaml at https://raw.githubusercontent.com/hubmapconsortium/search-api/test-release/src/search-schema/data/definitions/enums/organ_types.yaml
        or an error will be raised
    has_rui_info : string
        Accepts strings "true" or "false. Any other value will result in an error. If true, only datasets connected to 
        an sample that contain rui info will be returned. If false, only datasets that are NOT connected to samples
        containing rui info will be returned. By default, no filtering is performed. 
    dataset_status : string
        Filters results by dataset status. Accepted values are "Published", "QA", and "NEW". If a user only has access
        to published datasets and enters QA or New, an error will be raised. By default, no filtering is performed 

Returns
-------
json
    an array of each datatset's provenance info
tsv
    a text file of tab separated values where each row is a dataset and the columns include all its prov info
"""
@app.route('/datasets/prov-info', methods=['GET'])
def get_prov_info():
    # String constants
    HEADER_DATASET_UUID = 'dataset_uuid'
    HEADER_DATASET_HUBMAP_ID = 'dataset_hubmap_id'
    HEADER_DATASET_STATUS = 'dataset_status'
    HEADER_DATASET_GROUP_NAME = 'dataset_group_name'
    HEADER_DATASET_GROUP_UUID = 'dataset_group_uuid'
    HEADER_DATASET_DATE_TIME_CREATED = 'dataset_date_time_created'
    HEADER_DATASET_CREATED_BY_EMAIL = 'dataset_created_by_email'
    HEADER_DATASET_DATE_TIME_MODIFIED = 'dataset_date_time_modified'
    HEADER_DATASET_MODIFIED_BY_EMAIL = 'dataset_modified_by_email'
    HEADER_DATASET_LAB_ID = 'lab_id_or_name'
    HEADER_DATASET_DATA_TYPES = 'dataset_data_types'
    HEADER_DATASET_PORTAL_URL = 'dataset_portal_url'
    HEADER_FIRST_SAMPLE_HUBMAP_ID = 'first_sample_hubmap_id'
    HEADER_FIRST_SAMPLE_SUBMISSION_ID = 'first_sample_submission_id'
    HEADER_FIRST_SAMPLE_UUID = 'first_sample_uuid'
    HEADER_FIRST_SAMPLE_TYPE = 'first_sample_type'
    HEADER_FIRST_SAMPLE_PORTAL_URL = 'first_sample_portal_url'
    HEADER_ORGAN_HUBMAP_ID = 'organ_hubmap_id'
    HEADER_ORGAN_SUBMISSION_ID = 'organ_submission_id'
    HEADER_ORGAN_UUID = 'organ_uuid'
    HEADER_ORGAN_TYPE = 'organ_type'
    HEADER_DONOR_HUBMAP_ID = 'donor_hubmap_id'
    HEADER_DONOR_SUBMISSION_ID = 'donor_submission_id'
    HEADER_DONOR_UUID = 'donor_uuid'
    HEADER_DONOR_GROUP_NAME = 'donor_group_name'
    HEADER_RUI_LOCATION_HUBMAP_ID = 'rui_location_hubmap_id'
    HEADER_RUI_LOCATION_SUBMISSION_ID = 'rui_location_submission_id'
    HEADER_RUI_LOCATION_UUID = 'rui_location_uuid'
    HEADER_SAMPLE_METADATA_HUBMAP_ID = 'sample_metadata_hubmap_id'
    HEADER_SAMPLE_METADATA_SUBMISSION_ID = 'sample_metadata_submission_id'
    HEADER_SAMPLE_METADATA_UUID = 'sample_metadata_uuid'
    HEADER_PROCESSED_DATASET_UUID = 'processed_dataset_uuid'
    HEADER_PROCESSED_DATASET_HUBMAP_ID = 'processed_dataset_hubmap_id'
    HEADER_PROCESSED_DATASET_STATUS = 'processed_dataset_status'
    HEADER_PROCESSED_DATASET_PORTAL_URL = 'processed_dataset_portal_url'
    ASSAY_TYPES_URL = SchemaConstants.ASSAY_TYPES_YAML
    ORGAN_TYPES_URL = SchemaConstants.ORGAN_TYPES_YAML
    HEADER_PREVIOUS_VERSION_HUBMAP_IDS = 'previous_version_hubmap_ids'

    headers = [
        HEADER_DATASET_UUID, HEADER_DATASET_HUBMAP_ID, HEADER_DATASET_STATUS, HEADER_DATASET_GROUP_NAME,
        HEADER_DATASET_GROUP_UUID, HEADER_DATASET_DATE_TIME_CREATED, HEADER_DATASET_CREATED_BY_EMAIL,
        HEADER_DATASET_DATE_TIME_MODIFIED, HEADER_DATASET_MODIFIED_BY_EMAIL, HEADER_DATASET_LAB_ID,
        HEADER_DATASET_DATA_TYPES, HEADER_DATASET_PORTAL_URL, HEADER_FIRST_SAMPLE_HUBMAP_ID,
        HEADER_FIRST_SAMPLE_SUBMISSION_ID, HEADER_FIRST_SAMPLE_UUID, HEADER_FIRST_SAMPLE_TYPE,
        HEADER_FIRST_SAMPLE_PORTAL_URL, HEADER_ORGAN_HUBMAP_ID, HEADER_ORGAN_SUBMISSION_ID, HEADER_ORGAN_UUID,
        HEADER_ORGAN_TYPE, HEADER_DONOR_HUBMAP_ID, HEADER_DONOR_SUBMISSION_ID, HEADER_DONOR_UUID,
        HEADER_DONOR_GROUP_NAME, HEADER_RUI_LOCATION_HUBMAP_ID, HEADER_RUI_LOCATION_SUBMISSION_ID,
        HEADER_RUI_LOCATION_UUID, HEADER_SAMPLE_METADATA_HUBMAP_ID, HEADER_SAMPLE_METADATA_SUBMISSION_ID,
        HEADER_SAMPLE_METADATA_UUID, HEADER_PROCESSED_DATASET_UUID, HEADER_PROCESSED_DATASET_HUBMAP_ID,
        HEADER_PROCESSED_DATASET_STATUS, HEADER_PROCESSED_DATASET_PORTAL_URL, HEADER_PREVIOUS_VERSION_HUBMAP_IDS
    ]
    published_only = True

    # Token is not required, but if an invalid token is provided,
    # we need to tell the client with a 401 error
    validate_token_if_auth_header_exists(request)

    if user_in_hubmap_read_group(request):
        published_only = False

    # Parsing the organ types yaml has to be done here rather than calling schema.schema_triggers.get_organ_description
    # because that would require using a urllib request for each dataset
    response = requests.get(url=ORGAN_TYPES_URL, verify=False)

    if response.status_code == 200:
        yaml_file = response.text
        try:
            organ_types_dict = yaml.safe_load(yaml_file)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(e)

    # As above, we parse te assay type yaml here rather than calling the special method for it because this avoids
    # having to access the resource for every dataset.
    response = requests.get(url=ASSAY_TYPES_URL, verify=False)

    if response.status_code == 200:
        yaml_file = response.text
        try:
            assay_types_dict = yaml.safe_load(yaml_file)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(e)

    # Processing and validating query parameters
    accepted_arguments = ['format', 'organ', 'has_rui_info', 'dataset_status', 'group_uuid']
    return_json = False
    param_dict = {}
    if bool(request.args):
        for argument in request.args:
            if argument not in accepted_arguments:
                bad_request_error(f"{argument} is an unrecognized argument.")
        return_format = request.args.get('format')
        if return_format is not None:
            if return_format.lower() not in ['json', 'tsv']:
                bad_request_error(
                    "Invalid Format. Accepted formats are json and tsv. If no format is given, TSV will be the default")
            if return_format.lower() == 'json':
                return_json = True
        group_uuid = request.args.get('group_uuid')
        if group_uuid is not None:
            groups_by_id_dict = globus_groups.get_globus_groups_info()['by_id']
            if group_uuid not in groups_by_id_dict:
                bad_request_error(
                    f"Invalid Group UUID.")
            if not groups_by_id_dict[group_uuid]['data_provider']:
                bad_request_error(f"Invalid Group UUID. Group must be a data provider")
            param_dict['group_uuid'] = group_uuid
        organ = request.args.get('organ')
        if organ is not None:
            validate_organ_code(organ)
            param_dict['organ'] = organ
        has_rui_info = request.args.get('has_rui_info')
        if has_rui_info is not None:
            if has_rui_info.lower() not in ['true', 'false']:
                bad_request_error("Invalid value for 'has_rui_info'. Only values of true or false are acceptable")
            param_dict['has_rui_info'] = has_rui_info
        dataset_status = request.args.get('dataset_status')
        if dataset_status is not None:
            if dataset_status.lower() not in ['new', 'qa', 'published']:
                bad_request_error("Invalid Dataset Status. Must be 'new', 'qa', or 'published' Case-Insensitive")
            if published_only and dataset_status.lower() != 'published':
                bad_request_error(f"Invalid Dataset Status. No auth token given or token is not a member of HuBMAP-Read"
                                  " Group. If no token with HuBMAP-Read Group access is given, only datasets marked "
                                  "'Published' are available. Try again with a proper token, or change/remove "
                                  "dataset_status")
            if not published_only:
                param_dict['dataset_status'] = dataset_status

    # Instantiation of the list dataset_prov_list
    dataset_prov_list = []

    # Call to app_neo4j_queries to prepare and execute the database query
    prov_info = app_neo4j_queries.get_prov_info(neo4j_driver_instance, param_dict, published_only)

    # Each dataset's provinence info is placed into a dictionary
    for dataset in prov_info:
        internal_dict = collections.OrderedDict()
        internal_dict[HEADER_DATASET_UUID] = dataset['uuid']
        internal_dict[HEADER_DATASET_HUBMAP_ID] = dataset['hubmap_id']
        internal_dict[HEADER_DATASET_STATUS] = dataset['status']
        internal_dict[HEADER_DATASET_GROUP_NAME] = dataset['group_name']
        internal_dict[HEADER_DATASET_GROUP_UUID] = dataset['group_uuid']
        internal_dict[HEADER_DATASET_DATE_TIME_CREATED] = datetime.fromtimestamp(int(dataset['created_timestamp']/1000.0))
        internal_dict[HEADER_DATASET_CREATED_BY_EMAIL] = dataset['created_by_user_email']
        internal_dict[HEADER_DATASET_DATE_TIME_MODIFIED] = datetime.fromtimestamp(int(dataset['last_modified_timestamp']/1000.0))
        internal_dict[HEADER_DATASET_MODIFIED_BY_EMAIL] = dataset['last_modified_user_email']
        internal_dict[HEADER_DATASET_LAB_ID] = dataset['lab_dataset_id']

        # Data type codes are replaced with data type descriptions
        assay_description_list = []
        for item in dataset['data_types']:
            try:
                assay_description_list.append(assay_types_dict[item]['description'])
            # Some data types aren't given by their code in the assay types yaml and are instead given as an alt name.
            # In these cases, we have to search each assay type and see if the given code matches any alternate names.
            except KeyError:
                valid_key = False
                for each in assay_types_dict:
                    if valid_key is False:
                        if item in assay_types_dict[each]['alt-names']:
                            assay_description_list.append(assay_types_dict[each]['description'])
                            valid_key = True
                if valid_key is False:
                    assay_description_list.append(item)
        dataset['data_types'] = assay_description_list
        internal_dict[HEADER_DATASET_DATA_TYPES] = dataset['data_types']

        # If return_format was not equal to json, json arrays must be converted into comma separated lists for the tsv
        if return_json is False:
            internal_dict[HEADER_DATASET_DATA_TYPES] = ",".join(dataset['data_types'])

        internal_dict[HEADER_DATASET_PORTAL_URL] = app.config['DOI_REDIRECT_URL'].replace('<entity_type>', 'dataset').replace('<identifier>', dataset['uuid'])

        # first_sample properties are retrieved from its own dictionary
        if dataset['first_sample'] is not None:
            first_sample_hubmap_id_list = []
            first_sample_submission_id_list = []
            first_sample_uuid_list = []
            first_sample_type_list = []
            first_sample_portal_url_list = []
            for item in dataset['first_sample']:
                first_sample_hubmap_id_list.append(item['hubmap_id'])
                first_sample_submission_id_list.append(item['submission_id'])
                first_sample_uuid_list.append(item['uuid'])
                first_sample_type_list.append(item['specimen_type'])
                first_sample_portal_url_list.append(app.config['DOI_REDIRECT_URL'].replace('<entity_type>', 'sample').replace('<identifier>', item['uuid']))
            internal_dict[HEADER_FIRST_SAMPLE_HUBMAP_ID] = first_sample_hubmap_id_list
            internal_dict[HEADER_FIRST_SAMPLE_SUBMISSION_ID] = first_sample_submission_id_list
            internal_dict[HEADER_FIRST_SAMPLE_UUID] = first_sample_uuid_list
            internal_dict[HEADER_FIRST_SAMPLE_TYPE] = first_sample_type_list
            internal_dict[HEADER_FIRST_SAMPLE_PORTAL_URL] = first_sample_portal_url_list
            if return_json is False:
                internal_dict[HEADER_FIRST_SAMPLE_HUBMAP_ID] = ",".join(first_sample_hubmap_id_list)
                internal_dict[HEADER_FIRST_SAMPLE_SUBMISSION_ID] = ",".join(first_sample_submission_id_list)
                internal_dict[HEADER_FIRST_SAMPLE_UUID] = ",".join(first_sample_uuid_list)
                internal_dict[HEADER_FIRST_SAMPLE_TYPE] = ",".join(first_sample_type_list)
                internal_dict[HEADER_FIRST_SAMPLE_PORTAL_URL] = ",".join(first_sample_portal_url_list)

        # distinct_organ properties are retrieved from its own dictionary
        if dataset['distinct_organ'] is not None:
            distinct_organ_hubmap_id_list = []
            distinct_organ_submission_id_list = []
            distinct_organ_uuid_list = []
            distinct_organ_type_list = []
            for item in dataset['distinct_organ']:
                distinct_organ_hubmap_id_list.append(item['hubmap_id'])
                distinct_organ_submission_id_list.append(item['submission_id'])
                distinct_organ_uuid_list.append(item['uuid'])
                distinct_organ_type_list.append(organ_types_dict[item['organ']]['description'].lower())
            internal_dict[HEADER_ORGAN_HUBMAP_ID] = distinct_organ_hubmap_id_list
            internal_dict[HEADER_ORGAN_SUBMISSION_ID] = distinct_organ_submission_id_list
            internal_dict[HEADER_ORGAN_UUID] = distinct_organ_uuid_list
            internal_dict[HEADER_ORGAN_TYPE] = distinct_organ_type_list
            if return_json is False:
                internal_dict[HEADER_ORGAN_HUBMAP_ID] = ",".join(distinct_organ_hubmap_id_list)
                internal_dict[HEADER_ORGAN_SUBMISSION_ID] = ",".join(distinct_organ_submission_id_list)
                internal_dict[HEADER_ORGAN_UUID] = ",".join(distinct_organ_uuid_list)
                internal_dict[HEADER_ORGAN_TYPE] = ",".join(distinct_organ_type_list)

        # distinct_donor properties are retrieved from its own dictionary
        if dataset['distinct_donor'] is not None:
            distinct_donor_hubmap_id_list = []
            distinct_donor_submission_id_list = []
            distinct_donor_uuid_list = []
            distinct_donor_group_name_list = []
            for item in dataset['distinct_donor']:
                distinct_donor_hubmap_id_list.append(item['hubmap_id'])
                distinct_donor_submission_id_list.append(item['submission_id'])
                distinct_donor_uuid_list.append(item['uuid'])
                distinct_donor_group_name_list.append(item['group_name'])
            internal_dict[HEADER_DONOR_HUBMAP_ID] = distinct_donor_hubmap_id_list
            internal_dict[HEADER_DONOR_SUBMISSION_ID] = distinct_donor_submission_id_list
            internal_dict[HEADER_DONOR_UUID] = distinct_donor_uuid_list
            internal_dict[HEADER_DONOR_GROUP_NAME] = distinct_donor_group_name_list
            if return_json is False:
                internal_dict[HEADER_DONOR_HUBMAP_ID] = ",".join(distinct_donor_hubmap_id_list)
                internal_dict[HEADER_DONOR_SUBMISSION_ID] = ",".join(distinct_donor_submission_id_list)
                internal_dict[HEADER_DONOR_UUID] = ",".join(distinct_donor_uuid_list)
                internal_dict[HEADER_DONOR_GROUP_NAME] = ",".join(distinct_donor_group_name_list)

        # distinct_rui_sample properties are retrieved from its own dictionary
        if dataset['distinct_rui_sample'] is not None:
            rui_location_hubmap_id_list = []
            rui_location_submission_id_list = []
            rui_location_uuid_list = []
            for item in dataset['distinct_rui_sample']:
                rui_location_hubmap_id_list.append(item['hubmap_id'])
                rui_location_submission_id_list.append(item['submission_id'])
                rui_location_uuid_list.append(item['uuid'])
            internal_dict[HEADER_RUI_LOCATION_HUBMAP_ID] = rui_location_hubmap_id_list
            internal_dict[HEADER_RUI_LOCATION_SUBMISSION_ID] = rui_location_submission_id_list
            internal_dict[HEADER_RUI_LOCATION_UUID] = rui_location_uuid_list
            if return_json is False:
                internal_dict[HEADER_RUI_LOCATION_HUBMAP_ID] = ",".join(rui_location_hubmap_id_list)
                internal_dict[HEADER_RUI_LOCATION_SUBMISSION_ID] = ",".join(rui_location_submission_id_list)
                internal_dict[HEADER_RUI_LOCATION_UUID] = ",".join(rui_location_uuid_list)

        # distinct_metasample properties are retrieved from its own dictionary
        if dataset['distinct_metasample'] is not None:
            metasample_hubmap_id_list = []
            metasample_submission_id_list = []
            metasample_uuid_list = []
            for item in dataset['distinct_metasample']:
                metasample_hubmap_id_list.append(item['hubmap_id'])
                metasample_submission_id_list.append(item['submission_id'])
                metasample_uuid_list.append(item['uuid'])
            internal_dict[HEADER_SAMPLE_METADATA_HUBMAP_ID] = metasample_hubmap_id_list
            internal_dict[HEADER_SAMPLE_METADATA_SUBMISSION_ID] = metasample_submission_id_list
            internal_dict[HEADER_SAMPLE_METADATA_UUID] = metasample_uuid_list
            if return_json is False:
                internal_dict[HEADER_SAMPLE_METADATA_HUBMAP_ID] = ",".join(metasample_hubmap_id_list)
                internal_dict[HEADER_SAMPLE_METADATA_SUBMISSION_ID] = ",".join(metasample_submission_id_list)
                internal_dict[HEADER_SAMPLE_METADATA_UUID] = ",".join(metasample_uuid_list)

        # processed_dataset properties are retrived from its own dictionary
        if dataset['processed_dataset'] is not None:
            processed_dataset_uuid_list = []
            processed_dataset_hubmap_id_list = []
            processed_dataset_status_list = []
            processed_dataset_portal_url_list = []
            for item in dataset['processed_dataset']:
                processed_dataset_uuid_list.append(item['uuid'])
                processed_dataset_hubmap_id_list.append(item['hubmap_id'])
                processed_dataset_status_list.append(item['status'])
                processed_dataset_portal_url_list.append(app.config['DOI_REDIRECT_URL'].replace('<entity_type>', 'dataset').replace('<identifier>', item['uuid']))
            internal_dict[HEADER_PROCESSED_DATASET_UUID] = processed_dataset_uuid_list
            internal_dict[HEADER_PROCESSED_DATASET_HUBMAP_ID] = processed_dataset_hubmap_id_list
            internal_dict[HEADER_PROCESSED_DATASET_STATUS] = processed_dataset_status_list
            internal_dict[HEADER_PROCESSED_DATASET_PORTAL_URL] = processed_dataset_portal_url_list
            if return_json is False:
                internal_dict[HEADER_PROCESSED_DATASET_UUID] = ",".join(processed_dataset_uuid_list)
                internal_dict[HEADER_PROCESSED_DATASET_UUID] = ",".join(processed_dataset_hubmap_id_list)
                internal_dict[HEADER_PROCESSED_DATASET_UUID] = ",".join(processed_dataset_status_list)
                internal_dict[HEADER_PROCESSED_DATASET_UUID] = ",".join(processed_dataset_portal_url_list)


        if dataset['previous_version_hubmap_ids'] is not None:
            previous_version_hubmap_ids_list = []
            for item in dataset['previous_version_hubmap_ids']:
                previous_version_hubmap_ids_list.append(item)
            internal_dict[HEADER_PREVIOUS_VERSION_HUBMAP_IDS] = previous_version_hubmap_ids_list
            if return_json is False:
                internal_dict[HEADER_PREVIOUS_VERSION_HUBMAP_IDS] = ",".join(previous_version_hubmap_ids_list)

        # Each dataset's dictionary is added to the list to be returned
        dataset_prov_list.append(internal_dict)

    # if return_json is true, this dictionary is ready to be returned already
    if return_json:
        return jsonify(dataset_prov_list)

    # if return_json is false, the data must be converted to be returned as a tsv
    else:
        new_tsv_file = StringIO()
        writer = csv.DictWriter(new_tsv_file, fieldnames=headers, delimiter='\t')
        writer.writeheader()
        writer.writerows(dataset_prov_list)
        new_tsv_file.seek(0)
        output = Response(new_tsv_file, mimetype='text/tsv')
        output.headers['Content-Disposition'] = 'attachment; filename=prov-info.tsv'
        return output


"""
Get the complete provenance info for a given dataset

Authentication
-------
No token is required, however if a token is given it must be valid or an error will be raised. If no token with HuBMAP
Read Group access is given, only datasets designated as "published" will be returned

Query Parameters
-------
format : string
        Designates the output format of the returned data. Accepted values are "json" and "tsv". If none provided, by 
        default will return a tsv.

Path Parameters
-------
id : string
    A HuBMAP_ID or UUID for a dataset. If an invalid dataset id is given, an error will be raised    

Returns
-------
json
    an array of each datatset's provenance info
tsv
    a text file of tab separated values where each row is a dataset and the columns include all its prov info
"""
@app.route('/datasets/<id>/prov-info', methods=['GET'])
def get_prov_info_for_dataset(id):
    # Token is not required, but if an invalid token provided,
    # we need to tell the client with a 401 error
    validate_token_if_auth_header_exists(request)

    # Use the internal token to query the target entity
    # since public entities don't require user token
    token = get_internal_token()

    # Query target entity against uuid-api and neo4j and return as a dict if exists
    entity_dict = query_target_entity(id, token)
    normalized_entity_type = entity_dict['entity_type']

    # Only for Dataset
    if normalized_entity_type != 'Dataset':
        bad_request_error("The entity of given id is not a Dataset")

    # published/public datasets don't require token
    if entity_dict['status'].lower() != DATASET_STATUS_PUBLISHED:
        # Token is required and the user must belong to HuBMAP-READ group
        token = get_user_token(request, non_public_access_required=True)

    return_json = False
    dataset_prov_list = []
    if bool(request.args):
        return_format = request.args.get('format')
        if (return_format is not None) and (return_format.lower() == 'json'):
            return_json = True

    HEADER_DATASET_UUID = 'dataset_uuid'
    HEADER_DATASET_HUBMAP_ID = 'dataset_hubmap_id'
    HEADER_DATASET_STATUS = 'dataset_status'
    HEADER_DATASET_GROUP_NAME = 'dataset_group_name'
    HEADER_DATASET_GROUP_UUID = 'dataset_group_uuid'
    HEADER_DATASET_DATE_TIME_CREATED = 'dataset_date_time_created'
    HEADER_DATASET_CREATED_BY_EMAIL = 'dataset_created_by_email'
    HEADER_DATASET_DATE_TIME_MODIFIED = 'dataset_date_time_modified'
    HEADER_DATASET_MODIFIED_BY_EMAIL = 'dataset_modified_by_email'
    HEADER_DATASET_LAB_ID = 'lab_id_or_name'
    HEADER_DATASET_DATA_TYPES = 'dataset_data_types'
    HEADER_DATASET_PORTAL_URL = 'dataset_portal_url'
    HEADER_FIRST_SAMPLE_HUBMAP_ID = 'first_sample_hubmap_id'
    HEADER_FIRST_SAMPLE_SUBMISSION_ID = 'first_sample_submission_id'
    HEADER_FIRST_SAMPLE_UUID = 'first_sample_uuid'
    HEADER_FIRST_SAMPLE_TYPE = 'first_sample_type'
    HEADER_FIRST_SAMPLE_PORTAL_URL = 'first_sample_portal_url'
    HEADER_ORGAN_HUBMAP_ID = 'organ_hubmap_id'
    HEADER_ORGAN_SUBMISSION_ID = 'organ_submission_id'
    HEADER_ORGAN_UUID = 'organ_uuid'
    HEADER_ORGAN_TYPE = 'organ_type'
    HEADER_DONOR_HUBMAP_ID = 'donor_hubmap_id'
    HEADER_DONOR_SUBMISSION_ID = 'donor_submission_id'
    HEADER_DONOR_UUID = 'donor_uuid'
    HEADER_DONOR_GROUP_NAME = 'donor_group_name'
    HEADER_RUI_LOCATION_HUBMAP_ID = 'rui_location_hubmap_id'
    HEADER_RUI_LOCATION_SUBMISSION_ID = 'rui_location_submission_id'
    HEADER_RUI_LOCATION_UUID = 'rui_location_uuid'
    HEADER_SAMPLE_METADATA_HUBMAP_ID = 'sample_metadata_hubmap_id'
    HEADER_SAMPLE_METADATA_SUBMISSION_ID = 'sample_metadata_submission_id'
    HEADER_SAMPLE_METADATA_UUID = 'sample_metadata_uuid'
    HEADER_PROCESSED_DATASET_UUID = 'processed_dataset_uuid'
    HEADER_PROCESSED_DATASET_HUBMAP_ID = 'processed_dataset_hubmap_id'
    HEADER_PROCESSED_DATASET_STATUS = 'processed_dataset_status'
    HEADER_PROCESSED_DATASET_PORTAL_URL = 'processed_dataset_portal_url'
    ASSAY_TYPES_URL = SchemaConstants.ASSAY_TYPES_YAML
    ORGAN_TYPES_URL = SchemaConstants.ORGAN_TYPES_YAML

    headers = [
        HEADER_DATASET_UUID, HEADER_DATASET_HUBMAP_ID, HEADER_DATASET_STATUS, HEADER_DATASET_GROUP_NAME,
        HEADER_DATASET_GROUP_UUID, HEADER_DATASET_DATE_TIME_CREATED, HEADER_DATASET_CREATED_BY_EMAIL,
        HEADER_DATASET_DATE_TIME_MODIFIED, HEADER_DATASET_MODIFIED_BY_EMAIL, HEADER_DATASET_LAB_ID,
        HEADER_DATASET_DATA_TYPES, HEADER_DATASET_PORTAL_URL, HEADER_FIRST_SAMPLE_HUBMAP_ID,
        HEADER_FIRST_SAMPLE_SUBMISSION_ID, HEADER_FIRST_SAMPLE_UUID, HEADER_FIRST_SAMPLE_TYPE,
        HEADER_FIRST_SAMPLE_PORTAL_URL, HEADER_ORGAN_HUBMAP_ID, HEADER_ORGAN_SUBMISSION_ID, HEADER_ORGAN_UUID,
        HEADER_ORGAN_TYPE, HEADER_DONOR_HUBMAP_ID, HEADER_DONOR_SUBMISSION_ID, HEADER_DONOR_UUID,
        HEADER_DONOR_GROUP_NAME, HEADER_RUI_LOCATION_HUBMAP_ID, HEADER_RUI_LOCATION_SUBMISSION_ID,
        HEADER_RUI_LOCATION_UUID, HEADER_SAMPLE_METADATA_HUBMAP_ID, HEADER_SAMPLE_METADATA_SUBMISSION_ID,
        HEADER_SAMPLE_METADATA_UUID, HEADER_PROCESSED_DATASET_UUID, HEADER_PROCESSED_DATASET_HUBMAP_ID,
        HEADER_PROCESSED_DATASET_STATUS, HEADER_PROCESSED_DATASET_PORTAL_URL
    ]

    # Parsing the organ types yaml has to be done here rather than calling schema.schema_triggers.get_organ_description
    # because that would require using a urllib request for each dataset
    response = requests.get(url=ORGAN_TYPES_URL, verify=False)

    if response.status_code == 200:
        yaml_file = response.text
        try:
            organ_types_dict = yaml.safe_load(yaml_file)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(e)

    # As above, we parse te assay type yaml here rather than calling the special method for it because this avoids
    # having to access the resource for every dataset.
    response = requests.get(url=ASSAY_TYPES_URL, verify=False)

    if response.status_code == 200:
        yaml_file = response.text
        try:
            assay_types_dict = yaml.safe_load(yaml_file)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(e)

    hubmap_ids = schema_manager.get_hubmap_ids(id)

    # Get the target uuid if all good
    uuid = hubmap_ids['hm_uuid']
    dataset = app_neo4j_queries.get_individual_prov_info(neo4j_driver_instance, uuid)
    if dataset is None:
        bad_request_error("Query For this Dataset Returned no Records. Make sure this is a Primary Dataset")
    internal_dict = collections.OrderedDict()
    internal_dict[HEADER_DATASET_HUBMAP_ID] = dataset['hubmap_id']
    internal_dict[HEADER_DATASET_UUID] = dataset['uuid']
    internal_dict[HEADER_DATASET_STATUS] = dataset['status']
    internal_dict[HEADER_DATASET_GROUP_NAME] = dataset['group_name']
    internal_dict[HEADER_DATASET_GROUP_UUID] = dataset['group_uuid']
    internal_dict[HEADER_DATASET_DATE_TIME_CREATED] = datetime.fromtimestamp(int(dataset['created_timestamp'] / 1000.0))
    internal_dict[HEADER_DATASET_CREATED_BY_EMAIL] = dataset['created_by_user_email']
    internal_dict[HEADER_DATASET_DATE_TIME_MODIFIED] = datetime.fromtimestamp(
        int(dataset['last_modified_timestamp'] / 1000.0))
    internal_dict[HEADER_DATASET_MODIFIED_BY_EMAIL] = dataset['last_modified_user_email']
    internal_dict[HEADER_DATASET_LAB_ID] = dataset['lab_dataset_id']

    # Data type codes are replaced with data type descriptions
    assay_description_list = []
    for item in dataset['data_types']:
        try:
            assay_description_list.append(assay_types_dict[item]['description'])
        # Some data types aren't given by their code in the assay types yaml and are instead given as an alt name.
        # In these cases, we have to search each assay type and see if the given code matches any alternate names.
        except KeyError:
            valid_key = False
            for each in assay_types_dict:
                if valid_key is False:
                    if item in assay_types_dict[each]['alt-names']:
                        assay_description_list.append(assay_types_dict[each]['description'])
                        valid_key = True
            if valid_key is False:
                assay_description_list.append(item)
    dataset['data_types'] = assay_description_list
    internal_dict[HEADER_DATASET_DATA_TYPES] = dataset['data_types']
    if return_json is False:
        internal_dict[HEADER_DATASET_DATA_TYPES] = ",".join(dataset['data_types'])
    internal_dict[HEADER_DATASET_PORTAL_URL] = app.config['DOI_REDIRECT_URL'].replace('<entity_type>', 'dataset').replace(
        '<identifier>', dataset['uuid'])
    if dataset['first_sample'] is not None:
        first_sample_hubmap_id_list = []
        first_sample_submission_id_list = []
        first_sample_uuid_list = []
        first_sample_type_list = []
        first_sample_portal_url_list = []
        for item in dataset['first_sample']:
            first_sample_hubmap_id_list.append(item['hubmap_id'])
            first_sample_submission_id_list.append(item['submission_id'])
            first_sample_uuid_list.append(item['uuid'])
            first_sample_type_list.append(item['specimen_type'])
            first_sample_portal_url_list.append(
                app.config['DOI_REDIRECT_URL'].replace('<entity_type>', 'sample').replace('<identifier>', item['uuid']))
        internal_dict[HEADER_FIRST_SAMPLE_HUBMAP_ID] = first_sample_hubmap_id_list
        internal_dict[HEADER_FIRST_SAMPLE_SUBMISSION_ID] = first_sample_submission_id_list
        internal_dict[HEADER_FIRST_SAMPLE_UUID] = first_sample_uuid_list
        internal_dict[HEADER_FIRST_SAMPLE_TYPE] = first_sample_type_list
        internal_dict[HEADER_FIRST_SAMPLE_PORTAL_URL] = first_sample_portal_url_list
        if return_json is False:
            internal_dict[HEADER_FIRST_SAMPLE_HUBMAP_ID] = ",".join(first_sample_hubmap_id_list)
            internal_dict[HEADER_FIRST_SAMPLE_SUBMISSION_ID] = ",".join(first_sample_submission_id_list)
            internal_dict[HEADER_FIRST_SAMPLE_UUID] = ",".join(first_sample_uuid_list)
            internal_dict[HEADER_FIRST_SAMPLE_TYPE] = ",".join(first_sample_type_list)
            internal_dict[HEADER_FIRST_SAMPLE_PORTAL_URL] = ",".join(first_sample_portal_url_list)
    if dataset['distinct_organ'] is not None:
        distinct_organ_hubmap_id_list = []
        distinct_organ_submission_id_list = []
        distinct_organ_uuid_list = []
        distinct_organ_type_list = []
        for item in dataset['distinct_organ']:
            distinct_organ_hubmap_id_list.append(item['hubmap_id'])
            distinct_organ_submission_id_list.append(item['submission_id'])
            distinct_organ_uuid_list.append(item['uuid'])
            distinct_organ_type_list.append(organ_types_dict[item['organ']]['description'].lower())
        internal_dict[HEADER_ORGAN_HUBMAP_ID] = distinct_organ_hubmap_id_list
        internal_dict[HEADER_ORGAN_SUBMISSION_ID] = distinct_organ_submission_id_list
        internal_dict[HEADER_ORGAN_UUID] = distinct_organ_uuid_list
        internal_dict[HEADER_ORGAN_TYPE] = distinct_organ_type_list
        if return_json is False:
            internal_dict[HEADER_ORGAN_HUBMAP_ID] = ",".join(distinct_organ_hubmap_id_list)
            internal_dict[HEADER_ORGAN_SUBMISSION_ID] = ",".join(distinct_organ_submission_id_list)
            internal_dict[HEADER_ORGAN_UUID] = ",".join(distinct_organ_uuid_list)
            internal_dict[HEADER_ORGAN_TYPE] = ",".join(distinct_organ_type_list)
    if dataset['distinct_donor'] is not None:
        distinct_donor_hubmap_id_list = []
        distinct_donor_submission_id_list = []
        distinct_donor_uuid_list = []
        distinct_donor_group_name_list = []
        for item in dataset['distinct_donor']:
            distinct_donor_hubmap_id_list.append(item['hubmap_id'])
            distinct_donor_submission_id_list.append(item['submission_id'])
            distinct_donor_uuid_list.append(item['uuid'])
            distinct_donor_group_name_list.append(item['group_name'])
        internal_dict[HEADER_DONOR_HUBMAP_ID] = distinct_donor_hubmap_id_list
        internal_dict[HEADER_DONOR_SUBMISSION_ID] = distinct_donor_submission_id_list
        internal_dict[HEADER_DONOR_UUID] = distinct_donor_uuid_list
        internal_dict[HEADER_DONOR_GROUP_NAME] = distinct_donor_group_name_list
        if return_json is False:
            internal_dict[HEADER_DONOR_HUBMAP_ID] = ",".join(distinct_donor_hubmap_id_list)
            internal_dict[HEADER_DONOR_SUBMISSION_ID] = ",".join(distinct_donor_submission_id_list)
            internal_dict[HEADER_DONOR_UUID] = ",".join(distinct_donor_uuid_list)
            internal_dict[HEADER_DONOR_GROUP_NAME] = ",".join(distinct_donor_group_name_list)
    if dataset['distinct_rui_sample'] is not None:
        rui_location_hubmap_id_list = []
        rui_location_submission_id_list = []
        rui_location_uuid_list = []
        for item in dataset['distinct_rui_sample']:
            rui_location_hubmap_id_list.append(item['hubmap_id'])
            rui_location_submission_id_list.append(item['submission_id'])
            rui_location_uuid_list.append(item['uuid'])
        internal_dict[HEADER_RUI_LOCATION_HUBMAP_ID] = rui_location_hubmap_id_list
        internal_dict[HEADER_RUI_LOCATION_SUBMISSION_ID] = rui_location_submission_id_list
        internal_dict[HEADER_RUI_LOCATION_UUID] = rui_location_uuid_list
        if return_json is False:
            internal_dict[HEADER_RUI_LOCATION_HUBMAP_ID] = ",".join(rui_location_hubmap_id_list)
            internal_dict[HEADER_RUI_LOCATION_SUBMISSION_ID] = ",".join(rui_location_submission_id_list)
            internal_dict[HEADER_RUI_LOCATION_UUID] = ",".join(rui_location_uuid_list)
    if dataset['distinct_metasample'] is not None:
        metasample_hubmap_id_list = []
        metasample_submission_id_list = []
        metasample_uuid_list = []
        for item in dataset['distinct_metasample']:
            metasample_hubmap_id_list.append(item['hubmap_id'])
            metasample_submission_id_list.append(item['submission_id'])
            metasample_uuid_list.append(item['uuid'])
        internal_dict[HEADER_SAMPLE_METADATA_HUBMAP_ID] = metasample_hubmap_id_list
        internal_dict[HEADER_SAMPLE_METADATA_SUBMISSION_ID] = metasample_submission_id_list
        internal_dict[HEADER_SAMPLE_METADATA_UUID] = metasample_uuid_list
        if return_json is False:
            internal_dict[HEADER_SAMPLE_METADATA_HUBMAP_ID] = ",".join(metasample_hubmap_id_list)
            internal_dict[HEADER_SAMPLE_METADATA_SUBMISSION_ID] = ",".join(metasample_submission_id_list)
            internal_dict[HEADER_SAMPLE_METADATA_UUID] = ",".join(metasample_uuid_list)

    # processed_dataset properties are retrived from its own dictionary
    if dataset['processed_dataset'] is not None:
        processed_dataset_uuid_list = []
        processed_dataset_hubmap_id_list = []
        processed_dataset_status_list = []
        processed_dataset_portal_url_list = []
        for item in dataset['processed_dataset']:
            processed_dataset_uuid_list.append(item['uuid'])
            processed_dataset_hubmap_id_list.append(item['hubmap_id'])
            processed_dataset_status_list.append(item['status'])
            processed_dataset_portal_url_list.append(
                app.config['DOI_REDIRECT_URL'].replace('<entity_type>', 'dataset').replace('<identifier>',
                                                                                           item['uuid']))
        internal_dict[HEADER_PROCESSED_DATASET_UUID] = processed_dataset_uuid_list
        internal_dict[HEADER_PROCESSED_DATASET_HUBMAP_ID] = processed_dataset_hubmap_id_list
        internal_dict[HEADER_PROCESSED_DATASET_STATUS] = processed_dataset_status_list
        internal_dict[HEADER_PROCESSED_DATASET_PORTAL_URL] = processed_dataset_portal_url_list
        if return_json is False:
            internal_dict[HEADER_PROCESSED_DATASET_UUID] = ",".join(processed_dataset_uuid_list)
            internal_dict[HEADER_PROCESSED_DATASET_UUID] = ",".join(processed_dataset_hubmap_id_list)
            internal_dict[HEADER_PROCESSED_DATASET_UUID] = ",".join(processed_dataset_status_list)
            internal_dict[HEADER_PROCESSED_DATASET_UUID] = ",".join(processed_dataset_portal_url_list)

    dataset_prov_list.append(internal_dict)


    if return_json:
        return jsonify(dataset_prov_list[0])
    else:
        new_tsv_file = StringIO()
        writer = csv.DictWriter(new_tsv_file, fieldnames=headers, delimiter='\t')
        writer.writeheader()
        writer.writerows(dataset_prov_list)
        new_tsv_file.seek(0)
        output = Response(new_tsv_file, mimetype='text/tsv')
        output.headers['Content-Disposition'] = 'attachment; filename=prov-info.tsv'
        return output


"""
Get the information needed to generate the sankey on software-docs as a json.

Authentication
-------
No token is required or checked. The information returned is what is displayed in the public sankey

Query Parameters
-------
N/A

Path Parameters
-------
N/A

Returns
-------
json
    a json array. Each item in the array corresponds to a dataset. Each dataset has the values: dataset_group_name, 
    organ_type, dataset_data_types, and dataset_status, each of which is a string. 

"""
@app.route('/datasets/sankey_data', methods=['GET'])
def sankey_data():
    # String constants
    HEADER_DATASET_GROUP_NAME = 'dataset_group_name'
    HEADER_ORGAN_TYPE = 'organ_type'
    HEADER_DATASET_DATA_TYPES = 'dataset_data_types'
    HEADER_DATASET_STATUS = 'dataset_status'
    ASSAY_TYPES_URL = SchemaConstants.ASSAY_TYPES_YAML
    ORGAN_TYPES_URL = SchemaConstants.ORGAN_TYPES_YAML
    with open('sankey_mapping.json') as f:
        mapping_dict = json.load(f)
    # Parsing the organ types yaml has to be done here rather than calling schema.schema_triggers.get_organ_description
    # because that would require using a urllib request for each dataset
    response = requests.get(url=ORGAN_TYPES_URL, verify=False)

    if response.status_code == 200:
        yaml_file = response.text
        try:
            organ_types_dict = yaml.safe_load(yaml_file)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(e)

    # As above, we parse te assay type yaml here rather than calling the special method for it because this avoids
    # having to access the resource for every dataset.
    response = requests.get(url=ASSAY_TYPES_URL, verify=False)

    if response.status_code == 200:
        yaml_file = response.text
        try:
            assay_types_dict = yaml.safe_load(yaml_file)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(e)

    # Instantiation of the list dataset_prov_list
    dataset_sankey_list = []

    # Call to app_neo4j_queries to prepare and execute the database query
    sankey_info = app_neo4j_queries.get_sankey_info(neo4j_driver_instance)
    for dataset in sankey_info:
        internal_dict = collections.OrderedDict()
        internal_dict[HEADER_DATASET_GROUP_NAME] = dataset[HEADER_DATASET_GROUP_NAME]
        internal_dict[HEADER_ORGAN_TYPE] = organ_types_dict[dataset[HEADER_ORGAN_TYPE]]['description'].lower()
        # Data type codes are replaced with data type descriptions
        assay_description = ""
        try:
            assay_description = assay_types_dict[dataset[HEADER_DATASET_DATA_TYPES]]['description']
        # Some data types aren't given by their code in the assay types yaml and are instead given as an alt name.
        # In these cases, we have to search each assay type and see if the given code matches any alternate names.
        except KeyError:
            valid_key = False
            for each in assay_types_dict:
                if valid_key is False:
                    if dataset[HEADER_DATASET_DATA_TYPES] in assay_types_dict[each]['alt-names']:
                        assay_description = assay_types_dict[each]['description']
                        valid_key = True
            if valid_key is False:
                assay_description = dataset[HEADER_DATASET_DATA_TYPES]
        internal_dict[HEADER_DATASET_DATA_TYPES] = assay_description

        # Replace applicable Group Name and Data type with the value needed for the sankey via the mapping_dict
        internal_dict[HEADER_DATASET_STATUS] = dataset['dataset_status']
        if internal_dict[HEADER_DATASET_GROUP_NAME] in mapping_dict.keys():
            internal_dict[HEADER_DATASET_GROUP_NAME] = mapping_dict[internal_dict[HEADER_DATASET_GROUP_NAME]]
        if internal_dict[HEADER_DATASET_DATA_TYPES] in mapping_dict.keys():
            internal_dict[HEADER_DATASET_DATA_TYPES] = mapping_dict[internal_dict[HEADER_DATASET_DATA_TYPES]]

        # Each dataset's dictionary is added to the list to be returned
        dataset_sankey_list.append(internal_dict)
    return jsonify(dataset_sankey_list)


"""
Get the complete provenance info for all samples

Authentication
-------
Token that is part of the HuBMAP Read-Group is required.

Query Parameters
-------
    group_uuid : string
        Filters returned samples by a given group uuid. 

Returns
-------
json
    an array of each datatset's provenance info
"""
@app.route('/samples/prov-info', methods=['GET'])
def get_sample_prov_info():
    # String Constants
    HEADER_SAMPLE_UUID = "sample_uuid"
    HEADER_SAMPLE_LAB_ID = "lab_id_or_name"
    HEADER_SAMPLE_GROUP_NAME = "sample_group_name"
    HEADER_SAMPLE_CREATED_BY_EMAIL = "sample_created_by_email"
    HEADER_SAMPLE_HAS_METADATA = "sample_has_metadata"
    HEADER_SAMPLE_HAS_RUI_INFO = "sample_has_rui_info"
    HEADER_SAMPLE_DIRECT_ANCESTOR_ID = "sample_ancestor_id"
    HEADER_SAMPLE_DIRECT_ANCESTOR_ENTITY_TYPE = "sample_ancestor_entity"
    HEADER_SAMPLE_HUBMAP_ID = "sample_hubmap_id"
    HEADER_SAMPLE_SUBMISSION_ID = "sample_submission_id"
    HEADER_SAMPLE_TYPE = "sample_type"
    HEADER_DONOR_UUID = "donor_uuid"
    HEADER_DONOR_SUBMISSION_ID = "donor_submission_id"
    HEADER_DONOR_HUBMAP_ID = "donor_hubmap_id"
    HEADER_DONOR_HAS_METADATA = "donor_has_metadata"
    HEADER_ORGAN_UUID = "organ_uuid"
    HEADER_ORGAN_TYPE = "organ_type"
    HEADER_ORGAN_HUBMAP_ID = "organ_hubmap_id"
    HEADER_ORGAN_SUBMISSION_ID = "organ_submission_id"
    ORGAN_TYPES_URL = SchemaConstants.ORGAN_TYPES_YAML

    response = requests.get(url=ORGAN_TYPES_URL, verify=False)

    if response.status_code == 200:
        yaml_file = response.text
        try:
            organ_types_dict = yaml.safe_load(yaml_file)
        except yaml.YAMLError as e:
            raise yaml.YAMLError(e)

    # Processing and validating query parameters
    accepted_arguments = ['group_uuid']
    param_dict = {}  # currently the only filter is group_uuid, but in case this grows, we're using a dictionary
    if bool(request.args):
        for argument in request.args:
            if argument not in accepted_arguments:
                bad_request_error(f"{argument} is an unrecognized argument.")
        group_uuid = request.args.get('group_uuid')
        if group_uuid is not None:
            groups_by_id_dict = globus_groups.get_globus_groups_info()['by_id']
            if group_uuid not in groups_by_id_dict:
                bad_request_error(f"Invalid Group UUID.")
            if not groups_by_id_dict[group_uuid]['data_provider']:
                bad_request_error(f"Invalid Group UUID. Group must be a data provider")
            param_dict['group_uuid'] = group_uuid

    # Instantiation of the list sample_prov_list
    sample_prov_list = []

    # Call to app_neo4j_queries to prepare and execute database query
    prov_info = app_neo4j_queries.get_sample_prov_info(neo4j_driver_instance, param_dict)

    for sample in prov_info:

        # For cases where there is no sample of type organ above a given sample in the provenance, we check to see if
        # the given sample is itself an organ.
        organ_uuid = None
        organ_type = None
        organ_hubmap_id = None
        organ_submission_id = None
        if sample['organ_uuid'] is not None:
            organ_uuid = sample['organ_uuid']
            organ_type = organ_types_dict[sample['organ_organ_type']]['description'].lower()
            organ_hubmap_id = sample['organ_hubmap_id']
            organ_submission_id = sample['organ_submission_id']
        else:
            if sample['sample_specimen_type'] == "organ":
                organ_uuid = sample['sample_uuid']
                organ_type = organ_types_dict[sample['sample_organ']]['description'].lower()
                organ_hubmap_id = sample['sample_hubmap_id']
                organ_submission_id = sample['sample_submission_id']


        sample_has_metadata = False
        if sample['sample_metadata'] is not None:
            sample_has_metadata = True

        sample_has_rui_info = False
        if sample['sample_rui_info'] is not None:
            sample_has_rui_info = True

        donor_has_metadata = False
        if sample['donor_metadata'] is not None:
            donor_has_metadata = True

        internal_dict = collections.OrderedDict()
        internal_dict[HEADER_SAMPLE_UUID] = sample['sample_uuid']
        internal_dict[HEADER_SAMPLE_LAB_ID] = sample['lab_sample_id']
        internal_dict[HEADER_SAMPLE_GROUP_NAME] = sample['sample_group_name']
        internal_dict[HEADER_SAMPLE_CREATED_BY_EMAIL] = sample['sample_created_by_email']
        internal_dict[HEADER_SAMPLE_HAS_METADATA] = sample_has_metadata
        internal_dict[HEADER_SAMPLE_HAS_RUI_INFO] = sample_has_rui_info
        internal_dict[HEADER_SAMPLE_DIRECT_ANCESTOR_ID] = sample['sample_ancestor_id']
        internal_dict[HEADER_SAMPLE_TYPE] = sample['sample_specimen_type']
        internal_dict[HEADER_SAMPLE_HUBMAP_ID] = sample['sample_hubmap_id']
        internal_dict[HEADER_SAMPLE_SUBMISSION_ID] = sample['sample_submission_id']
        internal_dict[HEADER_SAMPLE_DIRECT_ANCESTOR_ENTITY_TYPE] = sample['sample_ancestor_entity']
        internal_dict[HEADER_DONOR_UUID] = sample['donor_uuid']
        internal_dict[HEADER_DONOR_HAS_METADATA] = donor_has_metadata
        internal_dict[HEADER_DONOR_HUBMAP_ID] = sample['donor_hubmap_id']
        internal_dict[HEADER_DONOR_SUBMISSION_ID] = sample['donor_submission_id']
        internal_dict[HEADER_ORGAN_UUID] = organ_uuid
        internal_dict[HEADER_ORGAN_TYPE] = organ_type
        internal_dict[HEADER_ORGAN_HUBMAP_ID] = organ_hubmap_id
        internal_dict[HEADER_ORGAN_SUBMISSION_ID] = organ_submission_id

        # Each sample's dictionary is added to the list to be returned
        sample_prov_list.append(internal_dict)
    return jsonify(sample_prov_list)


"""
Retrieve all unpublished datasets (datasets with status value other than 'Published' or 'Hold')

Authentication
-------
Requires HuBMAP Read-Group access. Authenticated in the gateway 

Query Parameters
-------
    format : string
        Determines the output format of the data. Allowable values are ("tsv"|"json")

Returns
-------
json
    an array of each unpublished dataset.
    fields: ("data_types", "donor_hubmap_id", "donor_submission_id", "hubmap_id", "organ", "organization", 
             "provider_experiment_id", "uuid")
tsv
    a text/tab-seperated-value document including each unpublished dataset.
    fields: ("data_types", "donor_hubmap_id", "donor_submission_id", "hubmap_id", "organ", "organization", 
             "provider_experiment_id", "uuid")
"""
@app.route('/datasets/unpublished', methods=['GET'])
def unpublished():
    # String constraints
    HEADER_DATA_TYPES = "data_types"
    HEADER_ORGANIZATION = "organization"
    HEADER_UUID = "uuid"
    HEADER_HUBMAP_ID = "hubmap_id"
    HEADER_ORGAN = "organ"
    HEADER_DONOR_HUBMAP_ID = "donor_hubmap_id"
    HEADER_SUBMISSION_ID = "donor_submission_id"
    HEADER_PROVIDER_EXPERIMENT_ID = "provider_experiment_id"

    headers = [
        HEADER_DATA_TYPES, HEADER_ORGANIZATION, HEADER_UUID, HEADER_HUBMAP_ID, HEADER_ORGAN, HEADER_DONOR_HUBMAP_ID,
        HEADER_SUBMISSION_ID, HEADER_PROVIDER_EXPERIMENT_ID
    ]

    # Processing and validating query parameters
    accepted_arguments = ['format']
    return_tsv = False
    if bool(request.args):
        for argument in request.args:
            if argument not in accepted_arguments:
                bad_request_error(f"{argument} is an unrecognized argument.")
        return_format = request.args.get('format')
        if return_format is not None:
            if return_format.lower() not in ['json', 'tsv']:
                bad_request_error(
                    "Invalid Format. Accepted formats are JSON and TSV. If no format is given, JSON will be the default")
            if return_format.lower() == 'tsv':
                return_tsv = True
    unpublished_info = app_neo4j_queries.get_unpublished(neo4j_driver_instance)
    if return_tsv:
        new_tsv_file = StringIO()
        writer = csv.DictWriter(new_tsv_file, fieldnames=headers, delimiter='\t')
        writer.writeheader()
        writer.writerows(unpublished_info)
        new_tsv_file.seek(0)
        output = Response(new_tsv_file, mimetype='text/tsv')
        output.headers['Content-Disposition'] = 'attachment; filename=unpublished-datasets.tsv'
        return output

    # if return_json is false, the data must be converted to be returned as a tsv
    else:
        return jsonify(unpublished_info)


####################################################################################################
## Internal Functions
####################################################################################################

"""
Throws error for 400 Bad Reqeust with message

Parameters
----------
err_msg : str
    The custom error message to return to end users
"""
def bad_request_error(err_msg):
    abort(400, description = err_msg)


"""
Throws error for 401 Unauthorized with message

Parameters
----------
err_msg : str
    The custom error message to return to end users
"""
def unauthorized_error(err_msg):
    abort(401, description = err_msg)


"""
Throws error for 403 Forbidden with message

Parameters
----------
err_msg : str
    The custom error message to return to end users
"""
def forbidden_error(err_msg):
    abort(403, description = err_msg)


"""
Throws error for 404 Not Found with message

Parameters
----------
err_msg : str
    The custom error message to return to end users
"""
def not_found_error(err_msg):
    abort(404, description = err_msg)


"""
Throws error for 500 Internal Server Error with message

Parameters
----------
err_msg : str
    The custom error message to return to end users
"""
def internal_server_error(err_msg):
    abort(500, description = err_msg)


"""
Parase the token from Authorization header

Parameters
----------
request : falsk.request
    The flask http request object
non_public_access_required : bool
    If a non-public access token is required by the request, default to False

Returns
-------
str
    The token string if valid
"""
def get_user_token(request, non_public_access_required = False):
    # Get user token from Authorization header
    # getAuthorizationTokens() also handles MAuthorization header but we are not using that here
    try:
        user_token = auth_helper_instance.getAuthorizationTokens(request.headers)
    except Exception:
        msg = "Failed to parse the Authorization token by calling commons.auth_helper.getAuthorizationTokens()"
        # Log the full stack trace, prepend a line with our message
        logger.exception(msg)
        internal_server_error(msg)

    # Further check the validity of the token if required non-public access
    if non_public_access_required:
        # When the token is a flask.Response instance,
        # it MUST be a 401 error with message.
        # That's how commons.auth_helper.getAuthorizationTokens() was designed
        if isinstance(user_token, Response):
            # We wrap the message in a json and send back to requester as 401 too
            # The Response.data returns binary string, need to decode
            unauthorized_error(user_token.get_data().decode())

        # By now the token is already a valid token
        # But we also need to ensure the user belongs to HuBMAP-Read group
        # in order to access the non-public entity
        # Return a 403 response if the user doesn't belong to HuBMAP-READ group
        if not user_in_hubmap_read_group(request):
            forbidden_error("Access not granted")

    return user_token


"""
Check if the user with token is in the HuBMAP-READ group

Parameters
----------
request : falsk.request
    The flask http request object that containing the Authorization header
    with a valid Globus groups token for checking group information

Returns
-------
bool
    True if the user belongs to HuBMAP-READ group, otherwise False
"""
def user_in_hubmap_read_group(request):
    if 'Authorization' not in request.headers:
        return False

    try:
        # The property 'hmgroupids' is ALWASYS in the output with using schema_manager.get_user_info()
        # when the token in request is a groups token
        user_info = schema_manager.get_user_info(request)
        hubmap_read_group_uuid = auth_helper_instance.groupNameToId('HuBMAP-READ')['uuid']
    except Exception as e:
        # Log the full stack trace, prepend a line with our message
        logger.exception(e)

        # If the token is not a groups token, no group information available
        # The commons.hm_auth.AuthCache would return a Response with 500 error message
        # We treat such cases as the user not in the HuBMAP-READ group
        return False


    return (hubmap_read_group_uuid in user_info['hmgroupids'])


"""
Validate the provided token when Authorization header presents

Parameters
----------
request : flask.request object
    The Flask http request object
"""
def validate_token_if_auth_header_exists(request):
    # No matter if token is required or not, when an invalid token provided,
    # we need to tell the client with a 401 error
    # HTTP header names are case-insensitive
    # request.headers.get('Authorization') returns None if the header doesn't exist
    if request.headers.get('Authorization') is not None:
        user_token = get_user_token(request)

        # When the Authoriztion header provided but the user_token is a flask.Response instance,
        # it MUST be a 401 error with message.
        # That's how commons.auth_helper.getAuthorizationTokens() was designed
        if isinstance(user_token, Response):
            # We wrap the message in a json and send back to requester as 401 too
            # The Response.data returns binary string, need to decode
            unauthorized_error(user_token.get_data().decode())

        # Also check if the parased token is invalid or expired
        # Set the second paremeter as False to skip group check
        user_info = auth_helper_instance.getUserInfo(user_token, False)

        if isinstance(user_info, Response):
            unauthorized_error(user_info.get_data().decode())


"""
Get the token for internal use only

Returns
-------
str
    The token string 
"""
def get_internal_token():
    return auth_helper_instance.getProcessSecret()


"""
Return the complete collection dict for a given raw collection dict

Parameters
----------
collection_dict : dict
    The raw collection dict returned by Neo4j

Returns
-------
dict
    A dictionary of complete collection detail with all the generated 'on_read_trigger' data
    The generated Collection.datasts contains only public datasets 
    if user/token doesn't have the right access permission
"""
def get_complete_public_collection_dict(collection_dict):
    # Use internal token to query entity since
    # no user token is required to access a public collection
    token = get_internal_token()

    # Collection.datasets is transient property and generated by the trigger method
    # We'll need to return all the properties including those
    # generated by `on_read_trigger` to have a complete result
    complete_dict = schema_manager.get_complete_entity_result(token, collection_dict)

    # Loop through Collection.datasets and only return the published/public datasets
    public_datasets = []
    for dataset in complete_dict['datasets']:
        if dataset['status'].lower() == DATASET_STATUS_PUBLISHED:
            public_datasets.append(dataset)

    # Modify the result and only show the public datasets in this collection
    complete_dict['datasets'] = public_datasets

    return complete_dict


"""
Generate 'before_create_triiger' data and create the entity details in Neo4j

Parameters
----------
request : flask.Request object
    The incoming request
normalized_entity_type : str
    One of the normalized entity types: Dataset, Collection, Sample, Donor
user_token: str
    The user's globus groups token
json_data_dict: dict
    The json request dict from user input

Returns
-------
dict
    A dict of all the newly created entity detials
"""
def create_entity_details(request, normalized_entity_type, user_token, json_data_dict):
    # Get user info based on request
    user_info_dict = schema_manager.get_user_info(request)

    # Create new ids for the new entity
    try:
        new_ids_dict_list = schema_manager.create_hubmap_ids(normalized_entity_type, json_data_dict, user_token, user_info_dict)
        new_ids_dict = new_ids_dict_list[0]
    # When group_uuid is provided by user, it can be invalid
    except schema_errors.NoDataProviderGroupException:
        # Log the full stack trace, prepend a line with our message
        if 'group_uuid' in json_data_dict:
            msg = "Invalid 'group_uuid' value, can't create the entity"
        else:
            msg = "The user does not have the correct Globus group associated with, can't create the entity"

        logger.exception(msg)
        bad_request_error(msg)
    except schema_errors.UnmatchedDataProviderGroupException:
        msg = "The user does not belong to the given Globus group, can't create the entity"
        logger.exception(msg)
        forbidden_error(msg)
    except schema_errors.MultipleDataProviderGroupException:
        msg = "The user has mutiple Globus groups associated with, please specify one using 'group_uuid'"
        logger.exception(msg)
        bad_request_error(msg)
    except KeyError as e:
        logger.exception(e)
        bad_request_error(e)
    except requests.exceptions.RequestException as e:
        msg = f"Failed to create new HuBMAP ids via the uuid-api service"
        logger.exception(msg)

        # Due to the use of response.raise_for_status() in schema_manager.create_hubmap_ids()
        # we can access the status codes from the exception
        status_code = e.response.status_code

        if status_code == 400:
            bad_request_error(e.response.text)
        if status_code == 404:
            not_found_error(e.response.text)
        else:
            internal_server_error(e.response.text)

    # Merge all the above dictionaries and pass to the trigger methods
    new_data_dict = {**json_data_dict, **user_info_dict, **new_ids_dict}

    try:
        # Use {} since no existing dict
        generated_before_create_trigger_data_dict = schema_manager.generate_triggered_data('before_create_trigger', normalized_entity_type, user_token, {}, new_data_dict)
    # If one of the before_create_trigger methods fails, we can't create the entity
    except schema_errors.BeforeCreateTriggerException:
        # Log the full stack trace, prepend a line with our message
        msg = "Failed to execute one of the 'before_create_trigger' methods, can't create the entity"
        logger.exception(msg)
        internal_server_error(msg)
    except schema_errors.NoDataProviderGroupException:
        # Log the full stack trace, prepend a line with our message
        if 'group_uuid' in json_data_dict:
            msg = "Invalid 'group_uuid' value, can't create the entity"
        else:
            msg = "The user does not have the correct Globus group associated with, can't create the entity"

        logger.exception(msg)
        bad_request_error(msg)
    except schema_errors.UnmatchedDataProviderGroupException:
        # Log the full stack trace, prepend a line with our message
        msg = "The user does not belong to the given Globus group, can't create the entity"
        logger.exception(msg)
        forbidden_error(msg)
    except schema_errors.MultipleDataProviderGroupException:
        # Log the full stack trace, prepend a line with our message
        msg = "The user has mutiple Globus groups associated with, please specify one using 'group_uuid'"
        logger.exception(msg)
        bad_request_error(msg)
    # If something wrong with file upload
    except schema_errors.FileUploadException as e:
        logger.exception(e)
        internal_server_error(e)
    except KeyError as e:
        # Log the full stack trace, prepend a line with our message
        logger.exception(e)
        bad_request_error(e)
    except Exception as e:
        logger.exception(e)
        internal_server_error(e)

    # Merge the user json data and generated trigger data into one dictionary
    merged_dict = {**json_data_dict, **generated_before_create_trigger_data_dict}

    # Filter out the merged_dict by getting rid of the transitent properties (not to be stored)
    # and properties with None value
    # Meaning the returned target property key is different from the original key
    # in the trigger method, e.g., Donor.image_files_to_add
    filtered_merged_dict = schema_manager.remove_transient_and_none_values(merged_dict, normalized_entity_type)

    # Create new entity
    try:
        # Important: `entity_dict` is the resulting neo4j dict, Python list and dicts are stored
        # as string expression literals in it. That's why properties like entity_dict['direct_ancestor_uuids']
        # will need to use ast.literal_eval() in the schema_triggers.py
        entity_dict = app_neo4j_queries.create_entity(neo4j_driver_instance, normalized_entity_type, filtered_merged_dict)
    except TransactionError:
        msg = "Failed to create the new " + normalized_entity_type
        # Log the full stack trace, prepend a line with our message
        logger.exception(msg)
        # Terminate and let the users know
        internal_server_error(msg)


    # Important: use `entity_dict` instead of `filtered_merged_dict` to keep consistent with the stored
    # string expression literals of Python list/dict being used with entity update, e.g., `image_files`
    # Important: the same property keys in entity_dict will overwrite the same key in json_data_dict
    # and this is what we wanted. Adding json_data_dict back is to include those `transient` properties
    # provided in the JSON input but not stored in neo4j, and will be needed for after_create_trigger/after_update_trigger,
    # e.g., `previous_revision_uuid`, `direct_ancestor_uuids`
    # Add user_info_dict because it may be used by after_update_trigger methods
    merged_final_dict = {**json_data_dict, **entity_dict, **user_info_dict}

    # Note: return merged_final_dict instead of entity_dict because
    # it contains all the user json data that the generated that entity_dict may not have
    return merged_final_dict


"""
Create multiple sample nodes and relationships with the source entity node

Parameters
----------
request : flask.Request object
    The incoming request
normalized_entity_type : str
    One of the normalized entity types: Dataset, Collection, Sample, Donor
user_token: str
    The user's globus groups token
json_data_dict: dict
    The json request dict from user input
count : int
    The number of samples to create

Returns
-------
list
    A list of all the newly generated ids via uuid-api
"""
def create_multiple_samples_details(request, normalized_entity_type, user_token, json_data_dict, count):
    # Get user info based on request
    user_info_dict = schema_manager.get_user_info(request)

    # Create new ids for the new entity
    try:
        new_ids_dict_list = schema_manager.create_hubmap_ids(normalized_entity_type, json_data_dict, user_token, user_info_dict, count)
    # When group_uuid is provided by user, it can be invalid
    except schema_errors.NoDataProviderGroupException:
        # Log the full stack trace, prepend a line with our message
        if 'group_uuid' in json_data_dict:
            msg = "Invalid 'group_uuid' value, can't create the entity"
        else:
            msg = "The user does not have the correct Globus group associated with, can't create the entity"

        logger.exception(msg)
        bad_request_error(msg)
    except schema_errors.UnmatchedDataProviderGroupException:
        # Log the full stack trace, prepend a line with our message
        msg = "The user does not belong to the given Globus group, can't create the entity"
        logger.exception(msg)
        forbidden_error(msg)
    except schema_errors.MultipleDataProviderGroupException:
        # Log the full stack trace, prepend a line with our message
        msg = "The user has mutiple Globus groups associated with, please specify one using 'group_uuid'"
        logger.exception(msg)
        bad_request_error(msg)
    except KeyError as e:
        # Log the full stack trace, prepend a line with our message
        logger.exception(e)
        bad_request_error(e)
    except requests.exceptions.RequestException as e:
        msg = f"Failed to create new HuBMAP ids via the uuid-api service"
        logger.exception(msg)

        # Due to the use of response.raise_for_status() in schema_manager.create_hubmap_ids()
        # we can access the status codes from the exception
        status_code = e.response.status_code

        if status_code == 400:
            bad_request_error(e.response.text)
        if status_code == 404:
            not_found_error(e.response.text)
        else:
            internal_server_error(e.response.text)

    # Use the same json_data_dict and user_info_dict for each sample
    # Only difference is the `uuid` and `hubmap_id` that are generated
    # Merge all the dictionaries and pass to the trigger methods
    new_data_dict = {**json_data_dict, **user_info_dict, **new_ids_dict_list[0]}

    # Instead of calling generate_triggered_data() for each sample, we'll just call it on the first sample
    # since all other samples will share the same generated data except `uuid` and `hubmap_id`
    # A bit performance improvement
    try:
        # Use {} since no existing dict
        generated_before_create_trigger_data_dict = schema_manager.generate_triggered_data('before_create_trigger', normalized_entity_type, user_token, {}, new_data_dict)
    # If one of the before_create_trigger methods fails, we can't create the entity
    except schema_errors.BeforeCreateTriggerException:
        # Log the full stack trace, prepend a line with our message
        msg = "Failed to execute one of the 'before_create_trigger' methods, can't create the entity"
        logger.exception(msg)
        internal_server_error(msg)
    except schema_errors.NoDataProviderGroupException:
        # Log the full stack trace, prepend a line with our message
        if 'group_uuid' in json_data_dict:
            msg = "Invalid 'group_uuid' value, can't create the entity"
        else:
            msg = "The user does not have the correct Globus group associated with, can't create the entity"

        logger.exception(msg)
        bad_request_error(msg)
    except schema_errors.UnmatchedDataProviderGroupException:
        # Log the full stack trace, prepend a line with our message
        msg = "The user does not belong to the given Globus group, can't create the entity"
        logger.exception(msg)
        forbidden_error(msg)
    except schema_errors.MultipleDataProviderGroupException:
        # Log the full stack trace, prepend a line with our message
        msg = "The user has mutiple Globus groups associated with, please specify one using 'group_uuid'"
        logger.exception(msg)
        bad_request_error(msg)
    except KeyError as e:
        # Log the full stack trace, prepend a line with our message
        logger.exception(e)
        bad_request_error(e)
    except Exception as e:
        logger.exception(e)
        internal_server_error(e)

    # Merge the user json data and generated trigger data into one dictionary
    merged_dict = {**json_data_dict, **generated_before_create_trigger_data_dict}

    # Filter out the merged_dict by getting rid of the transitent properties (not to be stored)
    # and properties with None value
    # Meaning the returned target property key is different from the original key
    # in the trigger method, e.g., Donor.image_files_to_add
    filtered_merged_dict = schema_manager.remove_transient_and_none_values(merged_dict, normalized_entity_type)

    samples_dict_list = []
    for new_ids_dict in new_ids_dict_list:
        # Just overwrite the `uuid` and `hubmap_id` that are generated
        # All other generated properties will stay the same across all samples
        sample_dict = {**filtered_merged_dict, **new_ids_dict}
        # Add to the list
        samples_dict_list.append(sample_dict)

    # Generate property values for the only one Activity node
    activity_data_dict = schema_manager.generate_activity_data(normalized_entity_type, user_token, user_info_dict)

    # Create new sample nodes and needed relationships as well as activity node in one transaction
    try:
        # No return value
        app_neo4j_queries.create_multiple_samples(neo4j_driver_instance, samples_dict_list, activity_data_dict, json_data_dict['direct_ancestor_uuid'])
    except TransactionError:
        msg = "Failed to create multiple samples"
        # Log the full stack trace, prepend a line with our message
        logger.exception(msg)
        # Terminate and let the users know
        internal_server_error(msg)

    # Return the generated ids for UI
    return new_ids_dict_list


"""
Execute 'after_create_triiger' methods

Parameters
----------
normalized_entity_type : str
    One of the normalized entity types: Dataset, Collection, Sample, Donor
user_token: str
    The user's globus groups token
merged_data_dict: dict
    The merged dict that contains the entity dict newly created and 
    information from user request json that are not stored in Neo4j
"""
def after_create(normalized_entity_type, user_token, merged_data_dict):
    try:
        # 'after_create_trigger' and 'after_update_trigger' don't generate property values
        # It just returns the empty dict, no need to assign value
        # Use {} since no new dict
        schema_manager.generate_triggered_data('after_create_trigger', normalized_entity_type, user_token, merged_data_dict, {})
    except schema_errors.AfterCreateTriggerException:
        # Log the full stack trace, prepend a line with our message
        msg = "The entity has been created, but failed to execute one of the 'after_create_trigger' methods"
        logger.exception(msg)
        internal_server_error(msg)
    except Exception as e:
        logger.exception(e)
        internal_server_error(e)


"""
Generate 'before_create_triiger' data and create the entity details in Neo4j

Parameters
----------
request : flask.Request object
    The incoming request
normalized_entity_type : str
    One of the normalized entity types: Dataset, Collection, Sample, Donor
user_token: str
    The user's globus groups token
json_data_dict: dict
    The json request dict
existing_entity_dict: dict
    Dict of the exiting entity information

Returns
-------
dict
    A dict of all the updated entity detials
"""
def update_entity_details(request, normalized_entity_type, user_token, json_data_dict, existing_entity_dict):
    # Get user info based on request
    user_info_dict = schema_manager.get_user_info(request)

    # Merge user_info_dict and the json_data_dict for passing to the trigger methods
    new_data_dict = {**user_info_dict, **json_data_dict}

    try:
        generated_before_update_trigger_data_dict = schema_manager.generate_triggered_data('before_update_trigger', normalized_entity_type, user_token, existing_entity_dict, new_data_dict)
    # If something wrong with file upload
    except schema_errors.FileUploadException as e:
        logger.exception(e)
        internal_server_error(e)
    # If one of the before_update_trigger methods fails, we can't update the entity
    except schema_errors.BeforeUpdateTriggerException:
        # Log the full stack trace, prepend a line with our message
        msg = "Failed to execute one of the 'before_update_trigger' methods, can't update the entity"
        logger.exception(msg)
        internal_server_error(msg)
    except Exception as e:
        logger.exception(e)
        internal_server_error(e)

    # Merge dictionaries
    merged_dict = {**json_data_dict, **generated_before_update_trigger_data_dict}

    # Filter out the merged_dict by getting rid of the transitent properties (not to be stored)
    # and properties with None value
    # Meaning the returned target property key is different from the original key
    # in the trigger method, e.g., Donor.image_files_to_add
    filtered_merged_dict = schema_manager.remove_transient_and_none_values(merged_dict, normalized_entity_type)

    # By now the filtered_merged_dict contains all user updates and all triggered data to be added to the entity node
    # Any properties in filtered_merged_dict that are not on the node will be added.
    # Any properties not in filtered_merged_dict that are on the node will be left as is.
    # Any properties that are in both filtered_merged_dict and the node will be replaced in the node. However, if any property in the map is null, it will be removed from the node.

    # Update the exisiting entity
    try:
        updated_entity_dict = app_neo4j_queries.update_entity(neo4j_driver_instance, normalized_entity_type, filtered_merged_dict, existing_entity_dict['uuid'])
    except TransactionError:
        msg = "Failed to update the entity with id " + id
        # Log the full stack trace, prepend a line with our message
        logger.exception(msg)
        # Terminate and let the users know
        internal_server_error(msg)

    # Important: use `updated_entity_dict` instead of `filtered_merged_dict` to keep consistent with the stored
    # string expression literals of Python list/dict being used with entity update, e.g., `image_files`
    # Important: the same property keys in entity_dict will overwrite the same key in json_data_dict
    # and this is what we wanted. Adding json_data_dict back is to include those `transient` properties
    # provided in the JSON input but not stored in neo4j, and will be needed for after_create_trigger/after_update_trigger,
    # e.g., `previous_revision_uuid`, `direct_ancestor_uuids`
    # Add user_info_dict because it may be used by after_update_trigger methods
    merged_final_dict = {**json_data_dict, **updated_entity_dict, **user_info_dict}

    # Use merged_final_dict instead of merged_dict because
    # merged_dict only contains properties to be updated, not all properties
    return merged_final_dict


"""
Execute 'after_update_triiger' methods

Parameters
----------
normalized_entity_type : str
    One of the normalized entity types: Dataset, Collection, Sample, Donor
user_token: str
    The user's globus groups token
entity_dict: dict
    The entity dict newly updated
"""
def after_update(normalized_entity_type, user_token, entity_dict):
    try:
        # 'after_create_trigger' and 'after_update_trigger' don't generate property values
        # It just returns the empty dict, no need to assign value
        # Use {} sicne no new dict
        schema_manager.generate_triggered_data('after_update_trigger', normalized_entity_type, user_token, entity_dict, {})
    except schema_errors.AfterUpdateTriggerException:
        # Log the full stack trace, prepend a line with our message
        msg = "The entity information has been updated, but failed to execute one of the 'after_update_trigger' methods"
        logger.exception(msg)
        internal_server_error(msg)
    except Exception as e:
        logger.exception(e)
        internal_server_error(e)


"""
Get target entity dict for the given id

Parameters
----------
id : str
    The uuid or hubmap_id of target entity
user_token: str
    The user's globus groups token from the incoming request

Returns
-------
dict
    A dictionary of entity details either from cache or new neo4j lookup
"""
def query_target_entity(id, user_token):
    entity_dict = None

    current_datetime = datetime.now()
    current_timestamp = int(round(current_datetime.timestamp()))

    # Check if the cached entity is found and still valid based on TTL upon request, delete if expired
    if (id in entity_cache) and (current_timestamp > entity_cache[id]['created_timestamp'] + SchemaConstants.REQUEST_CACHE_TTL):
        del entity_cache[id]

        logger.info(f'Deleted the expired entity cache of {id} at time {current_datetime}')

    # Use the cached data if found and still valid
    # Otherwise, make a fresh query and add to cache
    if (id in entity_cache) and (current_timestamp <= entity_cache[id]['created_timestamp'] + SchemaConstants.REQUEST_CACHE_TTL):
        entity_dict = entity_cache[id]['entity']

        logger.info(f'Using the valid cache data of entity {id} at time {current_datetime}')
    else:
        logger.info(f'Cache not found or expired. Making a new query to retrieve {id} at time {current_datetime}')
        
        try:
            """
            The dict returned by uuid-api that contains all the associated ids, e.g.:
            {
                "ancestor_id": "940f409ea5b96ff8d98a87d185cc28e2",
                "ancestor_ids": [
                    "940f409ea5b96ff8d98a87d185cc28e2"
                ],
                "email": "jamie.l.allen@vanderbilt.edu",
                "hm_uuid": "be5a8f1654364c9ea0ca3071ba48f260",
                "hubmap_id": "HBM272.FXQF.697",
                "submission_id": "VAN0032-RK-2-43",
                "time_generated": "2020-11-09 19:55:09",
                "type": "SAMPLE",
                "user_id": "83ae233d-6d1d-40eb-baa7-b6f636ab579a"
            }
            """
            # get_hubmap_ids() uses function cache to improve performance
            hubmap_ids = schema_manager.get_hubmap_ids(id)

            # Get the target uuid if all good
            uuid = hubmap_ids['hm_uuid']
            entity_dict = app_neo4j_queries.get_entity(neo4j_driver_instance, uuid)

            # The uuid exists via uuid-api doesn't mean it's also in Neo4j
            if not entity_dict:
                not_found_error(f"Entity of id: {id} not found in Neo4j")

            # Add to cache
            new_datetime = datetime.now()
            new_timestamp = int(round(new_datetime.timestamp()))

            entity_cache[id] = {
                'created_timestamp': new_timestamp,
                'entity': entity_dict
            }
        except requests.exceptions.RequestException as e:
            # Due to the use of response.raise_for_status() in schema_manager.get_hubmap_ids()
            # we can access the status codes from the exception
            status_code = e.response.status_code

            if status_code == 400:
                bad_request_error(e.response.text)
            if status_code == 404:
                not_found_error(e.response.text)
            else:
                internal_server_error(e.response.text)
    
    # Final return
    return entity_dict


"""
Always expect a json body from user request

request : Flask request object
    The Flask request passed from the API endpoint
"""
def require_json(request):
    if not request.is_json:
        bad_request_error("A json body and appropriate Content-Type header are required")


"""
Make a call to each search-api instance to reindex this entity node in elasticsearch

Parameters
----------
uuid : str
    The uuid of the target entity
user_token: str
    The user's globus groups token
"""
def reindex_entity(uuid, user_token):
    headers = create_request_headers(user_token)

    # Reindex the target entity against each configured search-api instance
    for search_api_url in app.config['SEARCH_API_URL_LIST']:
        logger.info(f"Making a call to search-api instance of {search_api_url} to reindex uuid: {uuid}")

        response = requests.put(f"{search_api_url}/reindex/{uuid}", headers = headers)

        # The reindex takes time, so 202 Accepted response status code indicates that
        # the request has been accepted for processing, but the processing has not been completed
        if response.status_code == 202:
            logger.info(f"The search-api instance of {search_api_url} has accepted the reindex request for uuid: {uuid}")
        else:
            logger.error(f"The search-api instance of {search_api_url} failed to initialize the reindex for uuid: {uuid}")


"""
Create a dict of HTTP Authorization header with Bearer token for making calls to uuid-api

Parameters
----------
user_token: str
    The user's globus groups token

Returns
-------
dict
    The headers dict to be used by requests
"""
def create_request_headers(user_token):
    auth_header_name = 'Authorization'
    auth_scheme = 'Bearer'

    headers_dict = {
        # Don't forget the space between scheme and the token value
        auth_header_name: auth_scheme + ' ' + user_token
    }

    return headers_dict


"""
Ensure the access level dir with leading and trailing slashes

dir_name : str
    The name of the sub directory corresponding to each access level

Returns
-------
str 
    One of the formatted dir path string: /public/, /protected/, /consortium/
"""
def access_level_prefix_dir(dir_name):
    if string_helper.isBlank(dir_name):
        return ''

    return hm_file_helper.ensureTrailingSlashURL(hm_file_helper.ensureBeginningSlashURL(dir_name))


"""
Ensures that a given organ code matches what is found on the organ_types yaml document

organ_code : str

Returns nothing. Raises bad_request_error is organ code not found on organ_types.yaml 
"""
def validate_organ_code(organ_code):
    yaml_file_url = SchemaConstants.ORGAN_TYPES_YAML

    # Function cache to improve performance
    response = schema_manager.make_request_get(yaml_file_url)

    if response.status_code == 200:
        yaml_file = response.text

        try:
            organ_types_dict = yaml.safe_load(response.text)
            
            if organ_code.upper() not in organ_types_dict:
                bad_request_error(f"Invalid Organ. Organ must be 2 digit code, case-insensitive located at {yaml_file_url}")
        except yaml.YAMLError as e:
            raise yaml.YAMLError(e)
    else:
        msg = f"Unable to fetch the: {yaml_file_url}"
        # Log the full stack trace, prepend a line with our message
        logger.exception(msg)

        logger.debug("======validate_organ_code() status code======")
        logger.debug(response.status_code)

        logger.debug("======validate_organ_code() response text======")
        logger.debug(response.text)

        # Terminate and let the users know
        internal_server_error(f"Failed to validate the organ code: {organ_code}")


####################################################################################################
## For local development/testing
####################################################################################################

if __name__ == "__main__":
    try:
        app.run(host='0.0.0.0', port="5002")
    except Exception as e:
        print("Error during starting debug server.")
        print(str(e))
        logger.error(e, exc_info=True)
        print("Error during startup check the log file for further information")
