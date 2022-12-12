from importlib import resources

import yaml

from aiidalab_qe import parameters

DEFAULT_PARAMETERS = yaml.safe_load(resources.read_text(parameters, "qeapp.yaml"))
