import logging
import logging.config
import yaml
import os
import re
from pathlib import Path
from os.path import dirname, realpath


if "LOG_LEVEL" not in os.environ:
    os.environ["LOG_LEVEL"] = "DEBUG"


def pattern():
    '''
    Pattern of the keyword used in YAML file to get values from the environment.
    
    Returns
    -------
    re.compile
        re.compile object.
    '''
    return re.compile(r'.*?\${(\w+)}.*?')


def constructor_env_variables(loader, node):
    '''
    Constructor of the env variables
    
    Parameters
    ----------
    loader : loader
        Loader.
    node : node
        Node.
    
    Returns
    -------
    loader object
        Loader object.
    '''
    value = loader.construct_scalar(node)
    match = pattern().findall(value)  
    if match:
        full_value = value
        for g in match:
            full_value = full_value.replace(
                f'${{{g}}}', os.environ.get(g, g)
            )
        return full_value
    return value


def get_logger(
    str_logger_name, 
    yaml_logging=Path(dirname(dirname(realpath(__file__))) + "/config/logging.yml")
):
    '''
    Get a custom logger.
    
    Parameters
    ----------
    str_logger_name : str
        The name of the logger.
    yaml_logging : str, optional
        Location of the YAML file for the logging configuration, by default "config/logging.yml"
    
    Returns
    -------
    logger
        The custom logger. 
    '''
    path_logging_yml = None
    if os.path.isfile(yaml_logging):
        path_logging_yml = Path(yaml_logging)
    if path_logging_yml is not None:
        tag = "!ENV"
        loader = yaml.SafeLoader
        loader.add_implicit_resolver(tag, pattern(), None)
        loader.add_constructor(tag, constructor_env_variables)
        with open(path_logging_yml, 'r') as stream:
            logger_config = yaml.load(stream, Loader=loader)
        logging.config.dictConfig(logger_config)
        logger = logging.getLogger(str_logger_name)
    else:
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - \
            [%(name)s] - [%(module)s] - %(funcName)s() - %(message)s')
        handler = logging.StreamHandler()
        handler.setLevel(level=logging.DEBUG)
        handler.setFormatter(formatter)
        logger = logging.getLogger(str_logger_name)
        logger.addHandler(handler)
        logger.propagate = False
    return logger