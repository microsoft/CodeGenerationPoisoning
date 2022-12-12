import yaml
from collections import namedtuple


class ConfigParsingException(Exception):
    pass


def parse_config(config_path):
    with open(config_path, 'r') as f:
        data = yaml.safe_load(f)

    validate_config(data)

    tasks_keys = set().union(*(d.keys() for d in data['tasks'])).union(data['task_defaults'].keys())

    Tasks = namedtuple('ConfigTasks', tasks_keys)
    Platform = namedtuple('ConfigPlatform', data['streaming_platform'].keys())

    platform_config = Platform(**data['streaming_platform'])
    tasks = []
    for task in data['tasks']:
        for key in tasks_keys:
            if key not in task:
                if key in data['task_defaults']:
                    task[key] = data['task_defaults'][key]
                else:
                    task[key] = None

        tasks.append(Tasks(**task))

    return platform_config, tasks


def validate_config(config_data):
    _check_type(config_data, dict)
    _check_in_obj('streaming_platform', config_data)
    _check_in_obj('broker_url', config_data['streaming_platform'])
    _check_in_obj('tasks', config_data)
    _check_key_in_all_obj('name', config_data['tasks'])
    _check_value_uniqueness('name', config_data['tasks'])


def _check_value_uniqueness(key, list_of_obj):
    data = []
    for element in list_of_obj:
        if element[key] in data:
            raise ConfigParsingException(f"Error in Corfiguration. "
                                         f"My guess: the values for {key} are not unique.")
        else:
            data.append(element[key])


def _check_key_in_all_obj(key, list_of_obj):
    for element in list_of_obj:
        _check_in_obj(key, element)


def _check_in_obj(key, obj):
    try:
        assert key in obj
    except AssertionError:
        raise ConfigParsingException(f"Error in Configuration. My guess: could not find {key} in {str(obj)}")


def _check_type(obj, check_type):
    try:
        assert isinstance(obj, check_type)
    except AssertionError:
        raise ConfigParsingException(f"Error in Configuration. My guess: {str(obj)} is not of type {check_type}")
