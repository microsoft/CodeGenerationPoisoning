import os
import yaml

CONFIG_YAML_PATH = os.path.expanduser('~/triggerflow_config.yaml')
EMPTY_CONFIG = {'triggerflow': {}}


def get_config():
    try:
        with open(CONFIG_YAML_PATH, 'r') as config_file:
            config = yaml.safe_load(config_file)
    except Exception:
        config = EMPTY_CONFIG

    return config


def get_dag_operator_config(operator: str):
    config = get_config()
    try:
        operator_config = config['dags']['operators'][operator]
    except KeyError:
        operator_config = {}

    return operator_config
