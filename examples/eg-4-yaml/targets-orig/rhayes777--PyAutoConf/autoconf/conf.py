import logging
import logging.config
import os
import shutil
from functools import wraps
from pathlib import Path
from typing import Optional, Union, Dict

import yaml

from autoconf.directory_config import RecursiveConfig, PriorConfigWrapper, AbstractConfig, family
from autoconf.exc import ConfigException
from autoconf.json_prior.config import JSONPriorConfig

logger = logging.getLogger(__name__)

LOGGING_CONFIG_FILE = "logging.yaml"


def get_matplotlib_backend():
    try:
        return instance["visualize"]["general"]["general"]["backend"]
    except KeyError:
        return "default"


class DictWrapper:
    def __init__(self, paths):
        self._dict = dict()
        self.paths = paths

    def __contains__(self, item):
        return item in self._dict

    def items(self):
        return self._dict.items()

    def __setitem__(self, key, value):
        if isinstance(key, str):
            key = key.lower()
        self._dict[key] = value

    def __getitem__(self, key):
        if isinstance(key, str):
            key = key.lower()
        try:
            return self._dict[key]
        except KeyError:
            raise KeyError(
                f"key {key} not found in paths {self.paths_string}"
            )

    @property
    def paths_string(self):
        return "\n".join(
            map(str, self.paths)
        )

    def __repr__(self):
        return repr(self._dict)

    def family(self, cls):
        for item in family(cls):
            try:
                return self[item]
            except KeyError:
                pass
        raise KeyError(
            f"config for {cls} or its parents not found in paths {self.paths_string}"
        )


class Config:
    def __init__(self, *config_paths, output_path: Union[str, Path] = "output"):
        """
        Singleton to manage configuration.

        Configuration is loaded using the __getitem__ syntax where the key entered
        can refer to a directory, file, section or item.

        Configuration is first attempted to be loaded from the directory indicated by the first
        config_path. If no configuration is found the second directory is searched and so on.
        This allows a default configuration to be defined with additional configuration overriding
        it.

        Parameters
        ----------
        config_paths
            Indicate directories where configuration is defined, in the order of priority with
            configuration in the first config_path overriding configuration in later config
            paths
        output_path
            The path where data should be saved.
        """
        for config_path in config_paths:
            if Path(config_path).name == "output":
                logger.warning(
                    f"{config_path} passed as config path. Did you mean to use output_path={config_path}?"
                )

        self._configs = list()
        self._dict = DictWrapper(
            self.paths
        )

        self.configs = list(map(
            RecursiveConfig,
            config_paths
        ))

        self.output_path = output_path

    @property
    def dict(self):
        """
        A dictionary containing configuration loaded from directories and files.

        Lazily recurse directories to load configuration.
        """
        if self._dict is None:
            self._dict = DictWrapper(
                self.paths
            )

            def recurse_config(
                    config,
                    d
            ):
                try:
                    for key, value in config.items():
                        if isinstance(
                                value,
                                AbstractConfig
                        ):
                            if key not in d:
                                d[key] = DictWrapper(
                                    self.paths
                                )
                            recurse_config(
                                value,
                                d=d[key]
                            )
                        else:
                            d[key] = value
                except KeyError as e:
                    logger.debug(e)

            for config_ in reversed(self._configs):
                recurse_config(config_, self._dict)
        return self._dict

    def configure_logging(self):
        """
        Set the most up to date logging configuration
        """
        logging_config = self.logging_config
        if logging_config is not None:
            logging.config.dictConfig(
                logging_config
            )

    @property
    def logging_config(self) -> Optional[Dict]:
        """
        Loading logging configuration from a YAML file
        from the most recently added config directory
        for which it exists.
        """
        for config in self.configs:
            path = config.path
            try:
                if LOGGING_CONFIG_FILE in os.listdir(
                        config.path
                ):
                    with open(
                            path / LOGGING_CONFIG_FILE
                    ) as f:
                        return yaml.safe_load(f)
            except FileNotFoundError:
                logger.debug(
                    f"No configuration found at path {config.path}"
                )
        return None

    @property
    def configs(self):
        return self._configs

    @configs.setter
    def configs(self, configs):
        """
        When the list of configs is updated this invalidates the current config
        dictionary
        """
        self._dict = None
        self._configs = configs

    def __getitem__(self, item):
        return self.dict[item]

    @property
    def paths(self):
        return [
            config.path
            for config
            in self._configs
        ]

    @property
    def prior_config(self) -> PriorConfigWrapper:
        """
        Configuration for priors. This indicates, for example, the mean and the width of priors
        for the attributes of given classes.
        """
        return PriorConfigWrapper([
            JSONPriorConfig.from_directory(
                path / "priors"
            )
            for path in self.paths
        ])

    def push(
            self,
            new_path: Union[str, Path],
            output_path: Optional[str] = None,
            keep_first: bool = False
    ):
        """
        Push a new configuration path. This overrides the existing config
        paths, with existing configs being used as a backup when a value
        cannot be found in an overriding config.

        Parameters
        ----------
        new_path
            A path to config directory
        output_path
            The path at which data should be output. If this is None then it remains
            unchanged
        keep_first
            If True the current priority configuration mains such.

        Raises
        ------
        ConfigException
            If the pushed path does not exist or does not contain at least one file
            with an expected configuration suffix
        """
        logger.debug(
            f"Pushing new config with path {new_path}"
        )

        if not Path(new_path).exists():
            raise ConfigException(f"{new_path} does not exist")

        suffixes = {
            Path(file).suffix
            for _, _, files
            in os.walk(new_path)
            for file in files
        }

        CONFIG_SUFFIXES = [
            ".yml",
            ".ini",
            ".json",
            ".yaml",
        ]

        if not any((
            suffix in suffixes
            for suffix in CONFIG_SUFFIXES
        )):
            raise ConfigException(
                f"{new_path} does not contain any files ending with {'/'.join(CONFIG_SUFFIXES)} recursively"
            )

        self.output_path = output_path or self.output_path

        try:
            if self.configs[0] == new_path or (
                    keep_first and len(self.configs) > 1 and self.configs[1] == new_path
            ):
                return
        except IndexError:
            pass

        new_config = RecursiveConfig(
            new_path
        )

        configs = list(filter(
            lambda config: config != new_config,
            self.configs
        ))
        if keep_first:
            self.configs = configs[:1] + [new_config] + configs[1:]
        else:
            self.configs = [new_config] + configs

        self.configure_logging()

    def register(self, file: str):
        """
        Add defaults for a given project

        Parameters
        ----------
        file
            The path to the project's __init__
        """
        self.push(
            Path(file).parent / "config",
            keep_first=True
        )


current_directory = Path(os.getcwd())

default = Config(
    current_directory / "config",
    output_path=current_directory / "output/"
)

instance = default


def output_path_for_test(
        temporary_path="temp",
        remove=True
):
    """
    Temporarily change the output path for the scope of a function
    (e.g. a test). Remove the files after the test has completed
    execution.

    Parameters
    ----------
    temporary_path
        The path to temporarily output files to
    remove
        Should the path be removed?

    Returns
    -------
    The original function, decorated
    """

    def remove_():
        if remove:
            shutil.rmtree(
                temporary_path,
                ignore_errors=True
            )

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            remove_()
            original_path = instance.output_path
            instance.output_path = temporary_path

            result = func(*args, **kwargs)

            remove_()
            instance.output_path = original_path

            return result

        return wrapper

    return decorator


def with_config(*path: str, value):
    """
    Create a decorator that swaps a value in configuration
    defined by path for the scope of a test.

    Parameters
    ----------
    path
        A path through config. e.g. "general", "output", "identifier_version"
    value
        The value to temporarily set for the config field

    Returns
    -------
    A decorator
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            config = instance
            for string in path[:-1]:
                config = config[string]

            original_value = config[path[-1]]
            config[path[-1]] = value

            result = func(*args, **kwargs)

            config[path[-1]] = original_value

            return result

        return wrapper

    return decorator
