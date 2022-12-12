import os
import yaml
import logging

def read_config(config):
    default_config = False
    if config is None:
        default_config = True
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config = os.path.join(script_dir, "config", "config.yaml")
    with open(config) as f:
        config_dict = yaml.safe_load(f)
    if default_config:
            config_dict["recipe_folder"] = os.path.join(os.path.dirname(script_dir),
                                                        config_dict["recipe_folder"])
    return config_dict

def get_logger(debug, log_file):
    if debug:
        file_log_level = logging.DEBUG
    else:
        file_log_level = logging.INFO

    log = logging.getLogger("master")
    log.setLevel(logging.DEBUG)

    # create file handler which logs even debug messages
    fh = logging.FileHandler(log_file)
    fh.setLevel(file_log_level)
    fh.setFormatter(logging.Formatter('%(asctime)-15s %(levelname)-8s %(message)s'))
    log.addHandler(fh)

    # create console handler to print errors to stdout
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    ch.setFormatter(logging.Formatter('%(levelname)-8s %(message)s'))
    log.addHandler(ch)
    return log
