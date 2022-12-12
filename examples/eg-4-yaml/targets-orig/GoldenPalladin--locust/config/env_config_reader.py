import logging
import yaml
from hyperclient.utils.data import DotDict

log = logging.getLogger(__name__)


class YamlTable(yaml.YAMLObject, dict):
    yaml_tag = "!Table"

    def __init__(self, data):
        super().__init__()
        self.data = data

    def items(self):
        items = []
        for key in self.data.keys():
            d = {k: v for k, v in zip(self.data["columns"], self.data[key])}
            items.append((key, d))
        return items


class _NotExistingClass:
    pass


class EnvConfig:
    def __init__(self, filepath, env: str = None):
        log.info(f'Loading config from [{filepath}]')
        with open(filepath) as env_config_file:
            self._yaml_contents = yaml.load(env_config_file)
        self._data = None
        self.update(env)

    def update(self, env):
        result = self._yaml_contents.get(env, dict())
        if 'default' in self._yaml_contents:
            result.update(self._yaml_contents['default'])
        self._data = DotDict(result)

    def __getattr__(self, item: str):
        return self._data[item]

    def __getitem__(self, item):
        return self.__getattr__(item)

    def get(self, item, default=_NotExistingClass()):
        try:
            return self.__getattr__(item)
        except KeyError:
            if not isinstance(default, _NotExistingClass):
                return default
            raise

    def __contains__(self, value):
        return value in self._data
