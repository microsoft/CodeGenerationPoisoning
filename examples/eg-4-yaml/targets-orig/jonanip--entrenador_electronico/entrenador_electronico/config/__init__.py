"""Automatically sets the logger and config files"""
from box import Box
import yaml
from entrenador_electronico.source.utils import get_config_path

def read_config():
    with open(get_config_path()) as yaml_file:
        config_dict = yaml.safe_load(yaml_file)
        return Box(config_dict, default_box=True)


config = read_config()