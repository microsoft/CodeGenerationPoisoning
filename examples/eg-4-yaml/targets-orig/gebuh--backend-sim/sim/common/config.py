
import yaml


def load_config(path):
    return yaml.safe_load(open(path))
