import yaml
import os
from pathlib import Path
from os.path import dirname, realpath
import re
from .logger import logger


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


def get_config(path_env_yaml=None):
    '''
    Get the configuration for the package.
    
    Parameters
    ----------
    path_env_yaml : str, optional
        Location of the YAML configuration file, by default None
    
    Returns
    -------
    dict
        A dictionary containing configuration parameters.
    '''

    if path_env_yaml is None:
        if "ENV_RUN" not in os.environ:
            logger.info("Environment not defined in os.environ, set DEVELOPMENT as default value.")
            os.environ["ENV_RUN"] = "DEVELOPMENT"
        str_env = os.environ["ENV_RUN"].lower()
        logger.info("Environment set to " + str_env + ".")
        path_env_yaml = Path(dirname(dirname(realpath(__file__))) + "/config/" + str_env + ".yml")

    if os.path.isfile(path_env_yaml):
        tag = "!ENV"
        loader = yaml.SafeLoader
        loader.add_implicit_resolver(tag, pattern(), None)
        loader.add_constructor(tag, constructor_env_variables)
        with open(path_env_yaml, 'r') as stream:
            dict_config = yaml.load(stream, Loader=loader)
    else:
        logger.warning("YAML file not found, loading default configuration.")
        dict_config = {
            "ENV": "DEFAULT", 
            "PING": "PONG", 
            "PATH_IN": "IN",
            "PATH_OUT": "OUT", 
            "PATH_SAVE": "SAVE"
        }

    return dict_config


dict_config = get_config()