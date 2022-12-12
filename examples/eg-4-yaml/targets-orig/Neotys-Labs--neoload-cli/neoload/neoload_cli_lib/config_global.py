import os
import yaml

from neoload_cli_lib import paths

__config_dir = paths.get_config_dir()
__config_file = os.path.join(__config_dir, "config-global.yaml")


def get_config_file():
    return __config_file


def list_attr(prefix=""):
    if prefix:
        return [(key, __config_global.get(key)) for key in __config_global.keys() if key.startswith(prefix)]
    else:
        return __config_global.items()


def get_attr(name, default=None):
    return __config_global.get(name, default)


def set_attr(name: object, value: object) -> object:
    if value is not None:
        __config_global[name] = value
    elif name in __config_global:
        del __config_global[name]
    _save()


def _save():
    os.makedirs(__config_dir, exist_ok=True)
    with open(get_config_file(), "w") as stream:
        yaml.dump(__config_global, stream)


def __load():
    if os.path.exists(get_config_file()):
        with open(get_config_file(), "r") as stream:
            return yaml.load(stream, Loader=yaml.BaseLoader)
    else:
        return {}


__config_global = __load()


def reset():
    global __config_global
    __config_global = {}
    _save()
