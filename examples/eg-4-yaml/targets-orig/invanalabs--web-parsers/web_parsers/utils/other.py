import uuid
import yaml


def generate_random_id():
    return str(uuid.uuid4().hex)


def yaml_to_json(yaml_data):
    return yaml.load(yaml_data, yaml.Loader)
