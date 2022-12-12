from os import path

import yaml

with open(path.join(path.dirname(__file__), 'config.yaml'), 'r') as yaml_file:
    Config = yaml.load(yaml_file)

