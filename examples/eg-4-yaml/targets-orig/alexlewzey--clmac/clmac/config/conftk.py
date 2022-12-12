"""tools for manipulating configurations"""
from pathlib import Path
from typing import Dict, Callable

import yaml

from clmac.config import definitions


def load_personal() -> Dict:
    """load personal settings file if exists else create file with null setting and return it"""
    return _load_yaml(definitions.PERSONAL_YAML, _set_default_personal)


def load_numkeys_0():
    return _load_yaml(path_yaml=definitions.NUMKEYS_YAML_0, default_setter=_set_default_numkeys)


def load_numkeys_1():
    return _load_yaml(path_yaml=definitions.NUMKEYS_YAML_1, default_setter=_set_default_numkeys)


def _load_yaml(path_yaml: Path, default_setter: Callable):
    try:
        with path_yaml.open('r') as f:
            settings = yaml.load(f, Loader=yaml.FullLoader)
    except FileNotFoundError:
        settings = default_setter(path_yaml)
    if not settings:
        settings = default_setter(path_yaml)
    return settings


def _set_default_personal() -> Dict:
    """return default config key value structure with null values and save as personal yaml file in config"""
    settings = {'gmail': '',
                'hotmail': '',
                'work_mail': '',
                'mobile': '',
                'name': '',
                'username': '',
                'address': '',
                }
    with definitions.PERSONAL_YAML.open('w') as f:
        yaml.dump(settings, f)
    return settings


def _set_default_numkeys(path_yaml: Path) -> Dict:
    """return default config key value structure with null values and save as personal yaml file in config"""
    settings = {
        1: '',
        2: '',
        3: '',
        4: '',
        5: '',
        6: '',
        7: '',
        8: '',
        9: '',
    }
    with path_yaml.open('w') as f:
        yaml.dump(settings, f)
    return settings
