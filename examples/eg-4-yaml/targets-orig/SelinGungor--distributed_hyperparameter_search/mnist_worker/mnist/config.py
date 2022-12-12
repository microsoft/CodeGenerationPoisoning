import yaml
import logging
import os

ROOT_DIR = os.path.dirname(os.path.realpath(__file__))


def get_config(config_section: str):
    logging.info("Reading the database configuration.. " + ROOT_DIR + "/mnist.yaml")
    config_yaml = ROOT_DIR + "/mnist.yaml"
    with open(config_yaml, 'r') as ymlfile:
        config = yaml.load(ymlfile)

    result = config[config_section]
    print(result)
    return result
