import os

import click
import yaml


class Config:
    def __init__(self, _filename=None):
        """Initialize a configuration object.

        :param load: load the configuration from the disk.
        """
        self.config = dict()
        self._f = None
        self._filename = _filename
        self._load()

    def filename(self):
        """The location of the configuration file."""
        return self._filename or os.path.join(
            click.get_app_dir("moduledev"), "config.yaml"
        )

    def _open(self):
        """
        Create the configuration file if it does not exist. Raise an error
        if it does not work.

        :return: an open file object in write mode
        """
        config_file = self.filename()
        config_dir = os.path.dirname(config_file)
        try:
            os.makedirs(config_dir, exist_ok=True)
        except Exception as e:
            raise SystemExit(f"Could not create directory {config_dir}:\n{e}")
        try:
            self._f = open(config_file, "w")
        except Exception as e:
            raise SystemExit(f"Could not open {config_file} for writing: {e}")

    def _load(self):
        """
        Load the configuration from the user home path if it exists. Exits with
        a parsing error in the event of a parsing exception.

        :return: A dictionary containing the nested YAML configuration; None if the
                 file is not found.
        """
        config_file = self.filename()
        if not os.path.exists(config_file):
            self._f = None
            return
        self._f = open(config_file)
        try:
            self.config = yaml.load(self._f, Loader=yaml.Loader)
        except yaml.YAMLError as exc:
            raise SystemExit(f"Error loading config file {config_file}:\n{exc}")
        self._f.close()

    def get(self, key=None):
        if key is not None:
            cfg = self.config.get(key, None)
        else:
            cfg = self.config
        return cfg

    def dump(self, key=None):
        """
        Format the configuration into a YAML string and return it.

        :param key: a confiuration key to dump. If not provided, the whole
                    configuration is dumped.

        :return: the configuration string
        """
        cfg = self.get(key)
        if not len(cfg):
            return ""
        if isinstance(cfg, dict):
            return yaml.dump(cfg)
        else:
            return str(cfg)

    def save(self):
        """Save the configuration."""
        self._open()
        self._f.write(self.dump())
        self._f.close()

    def set(self, setting, value):
        """set something in the configuration."""
        self.config[setting] = value
