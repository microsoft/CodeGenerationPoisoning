import logging.config
import os

import yaml

__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))


def read_logging_config():
    with open(os.path.join(__location__, 'logging.cfg'), 'r') as stream:
        try:
            logging_config = yaml.safe_load(stream)
            logging.config.dictConfig(logging_config)
            # do not log azure info messages
            logging.getLogger(
                'azure.core.pipeline.policies.http_logging_policy').setLevel(logging.WARNING)
            return logging
        except yaml.YAMLError as exc:
            print(exc)
        except Exception as ex:
            print(ex)
        return None


def read_azure_config():
    with open(os.path.join(__location__, 'azure.cfg'), 'r') as stream:
        try:
            azure_config = yaml.safe_load(stream)
            return \
                azure_config['az_storage_connection_str'],\
                azure_config['az_storage_blob_sas_url'],\
                azure_config['az_storage_blob_sas_token']
        except yaml.YAMLError as exc:
            print(exc)
        except Exception as ex:
            print(ex)
        return None, None, None
