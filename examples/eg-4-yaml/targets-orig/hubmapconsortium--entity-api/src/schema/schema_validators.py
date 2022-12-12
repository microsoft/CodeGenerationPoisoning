import yaml
import logging
import requests

# Local modules
from schema import schema_manager
from schema import schema_errors
from schema.schema_constants import SchemaConstants

logger = logging.getLogger(__name__)


####################################################################################################
## Entity Level Validators
####################################################################################################

"""
Validate the application specified in the custom HTTP header
for creating a new entity via POST or updating via PUT

Parameters
----------
normalized_type : str
    One of the types defined in the schema yaml: Dataset, Upload
request: Flask request
    The instance of Flask request passed in from application request
"""
def validate_application_header_before_entity_create(normalized_entity_type, request):
    # A list of applications allowed to create this new entity
    # Currently only ingest-api and ingest-pipeline are allowed
    # to create or update Dataset and Upload
    # Use lowercase for comparison
    applications_allowed = [SchemaConstants.INGEST_API_APP, SchemaConstants.INGEST_PIPELINE_APP]

    _validate_application_header(applications_allowed, request.headers)


##############################################################################################
## Property Level Validators
####################################################################################################

"""
Validate the target list has no duplicated items

Parameters
----------
property_key : str
    The target property key
normalized_type : str
    Submission
request: Flask request object
    The instance of Flask request passed in from application request
existing_data_dict : dict
    A dictionary that contains all existing entity properties
new_data_dict : dict
    The json data in request body, already after the regular validations
"""
def validate_no_duplicates_in_list(property_key, normalized_entity_type, request, existing_data_dict, new_data_dict):
    # Use lowercase for comparision via list comprehensions
    target_list = [v.lower() for v in new_data_dict[property_key]]
    if len(set(target_list)) != len(target_list):
        raise ValueError(f"The {property_key} field must only contain unique items")


"""
Validate the provided value of Dataset.status on update via PUT

Parameters
----------
property_key : str
    The target property key
normalized_type : str
    Dataset
request: Flask request object
    The instance of Flask request passed in from application request
existing_data_dict : dict
    A dictionary that contains all existing entity properties
new_data_dict : dict
    The json data in request body, already after the regular validations
"""
def validate_application_header_before_property_update(property_key, normalized_entity_type, request, existing_data_dict, new_data_dict):
    # A list of applications allowed to update this property
    # Currently only ingest-api and ingest-pipeline are allowed
    # to update Dataset.status or Upload.status
    # Use lowercase for comparison
    applications_allowed = [SchemaConstants.INGEST_API_APP, SchemaConstants.INGEST_PIPELINE_APP]

    _validate_application_header(applications_allowed, request.headers)


"""
Validate the provided value of Dataset.status on update via PUT

Parameters
----------
property_key : str
    The target property key
normalized_type : str
    Dataset
request: Flask request object
    The instance of Flask request passed in from application request
existing_data_dict : dict
    A dictionary that contains all existing entity properties
new_data_dict : dict
    The json data in request body, already after the regular validations
"""
def validate_dataset_status_value(property_key, normalized_entity_type, request, existing_data_dict, new_data_dict):
    # Use lowercase for comparison
    accepted_status_values = ['new', 'processing', 'published', 'qa', 'error', 'hold', 'invalid']
    new_status = new_data_dict[property_key].lower()

    if new_status not in accepted_status_values:
        raise ValueError("The provided status value of Dataset is not valid")

    if 'status' not in existing_data_dict:
        raise KeyError("Missing 'status' key in 'existing_data_dict' during calling 'validate_dataset_status_value()' validator method.")

    # If status == 'Published' already in Neo4j, then fail for any changes at all
    # Because once published, the dataset should be read-only
    if existing_data_dict['status'].lower() == SchemaConstants.DATASET_STATUS_PUBLISHED:
        raise ValueError("This dataset is already published, status change is not allowed")

    # HTTP header names are case-insensitive
    # request.headers.get('X-Hubmap-Application') returns None if the header doesn't exist
    app_header = request.headers.get(SchemaConstants.HUBMAP_APP_HEADER)

    # Change status to 'Published' can only happen via ingest-api 
    # because file system changes are needed
    if (new_status == SchemaConstants.DATASET_STATUS_PUBLISHED) and (app_header.lower() != SchemaConstants.INGEST_API_APP):
        raise ValueError(f"Dataset status change to 'Published' can only be made via {SchemaConstants.INGEST_API_APP}")

"""
Validate the sub_status field is also provided when Dataset.retraction_reason is provided on update via PUT

Parameters
----------
property_key : str
    The target property key
normalized_type : str
    Submission
request: Flask request object
    The instance of Flask request passed in from application request
existing_data_dict : dict
    A dictionary that contains all existing entity properties
new_data_dict : dict
    The json data in request body, already after the regular validations
"""
def validate_if_retraction_permitted(property_key, normalized_entity_type, request, existing_data_dict, new_data_dict):
    if 'status' not in existing_data_dict:
        raise KeyError("Missing 'status' key in 'existing_data_dict' during calling 'validate_if_retraction_permitted()' validator method.")

    # Only published dataset can be retracted
    if existing_data_dict['status'].lower() != SchemaConstants.DATASET_STATUS_PUBLISHED:
        raise ValueError("This dataset is not published, retraction is not allowed")

    # Only token in HuBMAP-Data-Admin group can retract a published dataset
    try:
        # The property 'hmgroupids' is ALWASYS in the output with using schema_manager.get_user_info()
        # when the token in request is a nexus_token
        user_info = schema_manager.get_user_info(request)
        hubmap_read_group_uuid = schema_manager.get_auth_helper_instance().groupNameToId('HuBMAP-READ')['uuid']
    except Exception as e:
        # Log the full stack trace, prepend a line with our message
        logger.exception(e)

        # If the token is not a nexus token, no group information available
        # The commons.hm_auth.AuthCache would return a Response with 500 error message
        # We treat such cases as the user not in the HuBMAP-READ group
        raise ValueError("Failed to parse the permission based on token, retraction is not allowed")

    if hubmap_read_group_uuid not in user_info['hmgroupids']:
        raise ValueError("Permission denied, retraction is not allowed")


"""
Validate the sub_status field is also provided when Dataset.retraction_reason is provided on update via PUT

Parameters
----------
property_key : str
    The target property key
normalized_type : str
    Submission
request: Flask request object
    The instance of Flask request passed in from application request
existing_data_dict : dict
    A dictionary that contains all existing entity properties
new_data_dict : dict
    The json data in request body, already after the regular validations
"""
def validate_sub_status_provided(property_key, normalized_entity_type, request, existing_data_dict, new_data_dict):
    if 'sub_status' not in new_data_dict:
        raise ValueError("Missing sub_status field when retraction_reason is provided")

"""
Validate the reaction_reason field is also provided when Dataset.sub_status is provided on update via PUT

Parameters
----------
property_key : str
    The target property key
normalized_type : str
    Submission
request: Flask request object
    The instance of Flask request passed in from application request
existing_data_dict : dict
    A dictionary that contains all existing entity properties
new_data_dict : dict
    The json data in request body, already after the regular validations
"""
def validate_retraction_reason_provided(property_key, normalized_entity_type, request, existing_data_dict, new_data_dict):
    if 'retraction_reason' not in new_data_dict:
        raise ValueError("Missing retraction_reason field when sub_status is provided")

"""
Validate the provided value of Dataset.sub_status on update via PUT

Parameters
----------
property_key : str
    The target property key
normalized_type : str
    Submission
request: Flask request object
    The instance of Flask request passed in from application request
existing_data_dict : dict
    A dictionary that contains all existing entity properties
new_data_dict : dict
    The json data in request body, already after the regular validations
"""
def validate_retracted_dataset_sub_status_value(property_key, normalized_entity_type, request, existing_data_dict, new_data_dict):
    # Use lowercase for comparison
    accepted_sub_status_values = ['retracted']
    sub_status = new_data_dict[property_key].lower()

    if sub_status not in accepted_sub_status_values:
        raise ValueError("Invalid sub_status value of the Dataset to be retracted")

"""
Validate the provided value of Upload.status on update via PUT

Parameters
----------
property_key : str
    The target property key
normalized_type : str
    Submission
request: Flask request object
    The instance of Flask request passed in from application request
existing_data_dict : dict
    A dictionary that contains all existing entity properties
new_data_dict : dict
    The json data in request body, already after the regular validations
"""
def validate_upload_status_value(property_key, normalized_entity_type, request, existing_data_dict, new_data_dict):
    # Use lowercase for comparison
    accepted_status_values = ['new', 'valid', 'invalid', 'error', 'reorganized', 'processing', 'submitted']
    new_status = new_data_dict[property_key].lower()

    if new_status not in accepted_status_values:
        raise ValueError(f"Invalid status value: {new_status}")


"""
Validate the provided value of Sample.specimen_type on create via POST and update via PUT

Parameters
----------
property_key : str
    The target property key
normalized_type : str
    Submission
request: Flask request object
    The instance of Flask request passed in from application request
existing_data_dict : dict
    A dictionary that contains all existing entity properties
new_data_dict : dict
    The json data in request body, already after the regular validations
"""
def validate_specimen_type(property_key, normalized_entity_type, request, existing_data_dict, new_data_dict):
    # Use lowercase for comparison
    defined_tissue_types = _get_tissue_types()
    specimen_type = new_data_dict[property_key].lower()

    if specimen_type not in defined_tissue_types:
        raise ValueError(f"Invalid specimen_type value: {specimen_type}")


####################################################################################################
## Internal Functions
####################################################################################################

"""
Validate the application specified in the custom HTTP header

Parameters
----------
applications_allowed : list
    A list of applications allowed, use lowercase for comparison
request_headers: Flask request.headers object, behaves like a dict
    The instance of Flask request.headers passed in from application request
"""
def _validate_application_header(applications_allowed, request_headers):
    # HTTP header names are case-insensitive
    # request_headers.get('X-Hubmap-Application') returns None if the header doesn't exist
    app_header = request_headers.get(SchemaConstants.HUBMAP_APP_HEADER)

    if not app_header:
        msg = f"Unbale to proceed due to missing {SchemaConstants.HUBMAP_APP_HEADER} header from request"
        raise schema_errors.MissingApplicationHeaderException(msg)

    # Use lowercase for comparing the application header value against the yaml
    if app_header.lower() not in applications_allowed:
        msg = f"Unable to proceed due to invalid {SchemaConstants.HUBMAP_APP_HEADER} header value: {app_header}"
        raise schema_errors.InvalidApplicationHeaderException(msg)


"""
Get the complete list of defined tissue types
https://github.com/hubmapconsortium/search-api/blob/master/src/search-schema/data/definitions/enums/tissue_sample_types.yaml

Returns
-------
list: The list of defined tissue types
"""
def _get_tissue_types():
    yaml_file_url = SchemaConstants.TISSUE_TYPES_YAML

    # Function cache to improve performance
    response = schema_manager.make_request_get(yaml_file_url)
    
    if response.status_code == 200:
        yaml_file = response.text

        try:
            tissue_types_dict = yaml.safe_load(response.text)

            # We don't need the description here, just a list of tissue types
            # Note: dict.keys() returns a dict, need to typecast to list
            tissue_types_list = list(tissue_types_dict.keys())

            # Add the 'other'
            tissue_types_list.append('other')
            
            return tissue_types_list
        except yaml.YAMLError as e:
            raise yaml.YAMLError(e)
    else:
        msg = f"Unable to fetch the: {yaml_file_url}"
        # Log the full stack trace, prepend a line with our message
        logger.exception(msg)

        logger.debug("======_get_tissue_types() status code======")
        logger.debug(response.status_code)

        logger.debug("======_get_tissue_types() response text======")
        logger.debug(response.text)

        # Also bubble up the error message
        raise requests.exceptions.RequestException(response.text)

