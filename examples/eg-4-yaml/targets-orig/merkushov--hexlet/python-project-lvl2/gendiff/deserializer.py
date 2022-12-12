import os
import json
import yaml


def _open_json_file(filepath):
    data = None

    try:
        data = json.load(open(filepath))
    except Exception:
        raise Exception('Can\'t decode JSON file')

    return data


def _open_yaml_file(filepath):
    data = None

    try:
        data = yaml.safe_load(open(filepath))
    except Exception:
        raise Exception('Can\'t decode YAML file')

    return data


def process(filepath):
    data = None

    root, ext = os.path.splitext(filepath)
    if (ext in ('.json', '.jsn')):
        data = _open_json_file(filepath)
    elif (ext in ('.yml', '.yaml')):
        data = _open_yaml_file(filepath)
    else:
        raise Exception('Unsupported input format')

    return data
