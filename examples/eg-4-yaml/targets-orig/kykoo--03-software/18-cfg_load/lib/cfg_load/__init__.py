#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Core functions of the cfg_load."""

# Core Library
import collections
import imp
import json
import logging
import os
import pprint
import sys
from copy import deepcopy
from datetime import datetime

# Third party
import mpu
import pytz
import yaml
from mpu.datastructures import dict_merge, set_dict_value
from six.moves import configparser

# First party
import cfg_load.paths
import cfg_load.remote
from cfg_load._version import __version__  # noqa


def load(filepath, load_raw=False, load_remote=True, **kwargs):
    """
    Load a configuration file.

    Parameters
    ----------
    filepath : str
        Path to the configuration file.
    load_raw : bool, optional (default: False)
        Load only the raw configuration file as a dict,
        without applying any logic to it.
    load_remote : bool, optional (default: True)
        Load files stored remotely, e.g. from a webserver or S3
    **kwargs
        Arbitrary keyword arguments which get passed to the loader functions.

    Returns
    -------
    config : Configuration
    """
    if filepath.lower().endswith(".yaml") or filepath.lower().endswith(".yml"):
        config = load_yaml(filepath, **kwargs)
    elif filepath.lower().endswith(".json"):
        config = load_json(filepath, **kwargs)
    elif filepath.lower().endswith(".ini"):
        config = load_ini(filepath, **kwargs)
    else:
        raise NotImplementedError(
            "Extension of the file '{}' was not " "recognized.".format(filepath)
        )
    if not load_raw:
        reference_dir = os.path.dirname(filepath)
        config = cfg_load.paths.make_paths_absolute(reference_dir, config)
        config = load_env(config)
        meta = mpu.io.get_file_meta(filepath)
        meta["parse_datetime"] = datetime.now(pytz.utc)
        config = Configuration(config, meta=meta, load_remote=load_remote)
    return config


def load_yaml(yaml_filepath, safe_load=True, **kwargs):
    """
    Load a YAML file.

    Parameters
    ----------
    yaml_filepath : str
    safe_load : bool, optional (default: True)
        This triggers the usage of yaml.safe_load.
        yaml.load can call any Python function and should only be used if the
        source of the configuration file is trusted.
    **kwargs
        Arbitrary keyword arguments which get passed to the loader functions.

    Returns
    -------
    config : dict
    """
    with open(yaml_filepath, "r") as stream:
        if safe_load:
            config = yaml.safe_load(stream, **kwargs)
        else:
            config = yaml.load(stream, **kwargs)
    return config


def load_json(json_filepath, **kwargs):
    """
    Load a JSON file.

    Parameters
    ----------
    json_filepath : str
    **kwargs
        Arbitrary keyword arguments which get passed to the loader functions.

    Returns
    -------
    config : dict
    """
    with open(json_filepath, "r") as stream:
        config = json.load(stream, **kwargs)
    return config


def load_ini(ini_filepath, **kwargs):
    """
    Load a ini file.

    Parameters
    ----------
    ini_filepath : str
    **kwargs
        Arbitrary keyword arguments which get passed to the loader functions.

    Returns
    -------
    config : OrderedDict
    """
    config = configparser.ConfigParser(**kwargs)
    config.read(ini_filepath)
    return config._sections


def load_env(config):
    """
    Load environment variables in config.

    Parameters
    ----------
    config : dict

    Returns
    -------
    config : dict
    """
    logger = logging.getLogger(__name__)
    for env_name in os.environ:
        if env_name.startswith("_"):
            continue
        if env_name in config:
            if isinstance(config[env_name], str):
                config[env_name] = os.environ[env_name]
            elif isinstance(config[env_name], (list, dict, float, int, bool)):
                config[env_name] = json.loads(os.environ[env_name])
            else:
                logger.warning(
                    "Configuration value was {} of type {}, but "
                    "is overwritten with a string from the "
                    "environment"
                )
                config[env_name] = os.environ[env_name]
    return config


class Configuration(collections.Mapping):
    """
    Configuration class.

    Essentially, this is an immutable dictionary.

    Parameters
    ----------
    cfg_dict : dict
    meta : dict
    load_remote : bool
    """

    def __init__(self, cfg_dict, meta, load_remote=True):
        self._dict = deepcopy(cfg_dict)  # make a copy
        self._hash = None
        meta["load_remote"] = load_remote
        self._add_meta(meta)
        self.modules = {}
        self._load_modules(self._dict)
        if load_remote:
            self._load_remote(self._dict)

    def __getitem__(self, key):
        return self._dict[key]

    def __len__(self):
        return len(self._dict)

    def __iter__(self):
        return iter(self._dict)

    def __eq__(self, other):
        return self._dict == other._dict

    def set(self, key, value):
        """
        Set a value in the configuration.

        Although it is discouraged to do so, it might be necessary in some
        cases.

        If you need to overwrite a dictionary, then you should do:

        >> inner_dict = cfg['key']
        >> inner_dict['inner_key'] = 'new_value'
        >> cfg.set('key', inner_dict)
        """
        self._dict[key] = value
        return self

    def __str__(self):
        class_name = self.__class__.__name__
        return "{class_name}({cfg_filepath})".format(
            class_name=class_name, cfg_filepath=self.meta["filepath"]
        )

    def __repr__(self):
        class_name = self.__class__.__name__
        return (
            "{class_name}(cfg_dict={cfg_dict}, meta={meta}, "
            "load_remote={load_remote})".format(
                class_name=class_name,
                cfg_dict=self._dict,
                meta=self.meta,
                load_remote=self.meta["load_remote"],
            )
        )

    def pformat(self, indent=4, meta=False):
        """
        Pretty-format the configuration.

        Parameters
        ----------
        indent : int
        meta : bool
            Print metadata

        Returns
        -------
        pretty_format_cfg : str
        """
        str_ = ""
        if meta:
            str_ += "Configuration:"
            str_ += "Meta:"
            str_ += "\tSource: {}".format(self.meta["filepath"])
            str_ += "\tParsed at: {}".format(self.meta["parse_datetime"])
            str_ += "Values:"
        pp = pprint.PrettyPrinter(indent=indent)
        str_ += pp.pformat(self._dict)
        return str_

    def _add_meta(self, meta):
        """
        Add meta data to configuration.

        Parameters
        ----------
        config : dict
        meta : dict

        Returns
        -------
        config : dict
        """
        assert isinstance(meta, dict), "type(meta)={}, meta={}".format(type(meta), meta)
        assert "parse_datetime" in meta, "meta does not contain parse_datetime"
        self.meta = meta
        self.meta["filepath"] = os.path.abspath(meta["filepath"])
        return self

    def _load_modules(self, config):
        """
        Every key [SOMETHING]_module_path is loaded as a module.

        The module is accessible at config.modules['SOMETHING'].

        Parameters
        ----------
        config : dict

        Returns
        -------
        config : dict
        """
        keyword = "_module_path"
        if isinstance(config, list):
            for i, el in enumerate(config):
                config[i] = self._load_modules(config[i])
        elif isinstance(config, dict):
            for key in list(config.keys()):
                if hasattr(key, "endswith"):
                    if key.startswith("_"):
                        continue
                    if key.endswith(keyword):
                        # Handler
                        sys.path.insert(1, os.path.dirname(config[key]))
                        loaded_module = imp.load_source("foobar", config[key])
                        target_key = key[: -len(keyword)]
                        self.modules[target_key] = loaded_module
                if type(config[key]) is dict:
                    config[key] = self._load_modules(config[key])
        return config

    def _load_remote(self, config):
        """
        Load remote paths.

        Every key ending with `_load_url` has to have `source_url` and
        `sink_path`. Sources which are AWS S3 URLs and URLs starting with
        http(s) will be loaded automatically and stored in the sink. A `policy`
        parameter can specify if it should be `load_always` or
        `load_if_missing`.

        Parameters
        ----------
        config : dict

        Returns
        -------
        config : dict
        """
        keyword = "_load_url"
        if isinstance(config, list):
            for i, el in enumerate(config):
                config[i] = self._load_remote(config[i])
        elif isinstance(config, dict):
            for key in list(config.keys()):
                if hasattr(key, "endswith"):
                    if key.startswith("_"):
                        continue
                    if key.endswith(keyword):
                        # Handler
                        has_dl_info = (
                            "source_url" in config[key] and "sink_path" in config[key]
                        )
                        if not has_dl_info:
                            logging.warning(
                                "The key '{}' has not both keys "
                                "'source_url' and 'sink_path' ".format(key)
                            )
                        else:
                            source = config[key]["source_url"]
                            sink = config[key]["sink_path"]
                            cfg_load.remote.load(source, sink)
                if type(config[key]) is dict:
                    config[key] = self._load_remote(config[key])
        return config

    def update(self, other):
        """
        Update this configuration with values of the other configuration.

        Paramters
        ---------
        other : Configuration

        Returns
        -------
        updated_config : Configuration
        """
        this_dict = deepcopy(self._dict)
        other_dict = deepcopy(other._dict)
        merged_dict = dict_merge(this_dict, other_dict, merge_method="take_right_deep")
        cfg = Configuration(merged_dict, other.meta)
        return cfg

    def apply_env(self, env_mapping):
        """
        Apply environment variables to overwrite the current Configuration.

        The env_mapping has the following structure (in YAML):

        ```
        - env_name: "AWS_REGION"
          keys: ["AWS", "REGION"]
          converter: str
        - env_name: "AWS_IS_ENABLED"
          keys: ["AWS", "IS_ENABLED"]
          converter: bool
        ```

        If the env_name is not an ENVIRONMENT variable, then nothing is done.
        If an ENVIRONMENT variable is not defined in env_mapping, nothing is
        done.

        Known converters:

        * bool
        * str
        * str2str_or_none
        * int
        * float
        * json

        Parameters
        ----------
        env_mapping : Configuration

        Returns
        -------
        update_config : Configuration
        """
        converters = {
            "str": str,
            "str2str_or_none": mpu.string.str2str_or_none,
            "bool": mpu.string.str2bool,
            "int": int,
            "float": float,
            "json": json.loads,
        }
        new_dict = deepcopy(self._dict)
        for el in env_mapping:
            env_name = el["env_name"]
            if env_name not in os.environ:
                continue
            convert = converters[el["converter"]]
            value = convert(os.environ[env_name])
            set_dict_value(new_dict, el["keys"], value)
        return Configuration(new_dict, self.meta)

    def to_dict(self):
        """
        Return a dictionary representation of the configuration.

        This does NOT contain the metadata connected with the configuration.
        It is discuraged to use this in production as it loses the metadata
        and guarantees connected with the configuraiton object.

        Returns
        -------
        config : dict
        """
        return self._dict
