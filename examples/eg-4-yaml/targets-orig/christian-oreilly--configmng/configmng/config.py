from pathlib import Path
from collections.abc import MutableMapping
from tempfile import NamedTemporaryFile
from warnings import warn
from pykwalify.core import Core
from pykwalify.errors import SchemaError
import typing
from typing import List
import os
import json
import re

import yaml
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

from .schema import Schema
from .utils import ConfigMngLoader, update, get_node
from .provenance import ConfigProv


def check_regex_key(map, key):
    if key in map:
        return map[key]

    for map_key in map:
        if "regex" in map_key:
            regex = map_key.split(";")[1]
            pattern = re.compile(regex)
            if pattern.match(key):
                return map[map_key]

    raise TypeError



def get_schema_node(schema, path, key):
    obj_to_return = schema
    for level in path:
        if "mapping" in obj_to_return:
            obj_to_return = check_regex_key(obj_to_return["mapping"], level)
        else:
            raise NotImplementedError
    if "mapping" in obj_to_return:
        return check_regex_key(obj_to_return["mapping"], key)
    raise NotImplementedError


def get_schema_key_type(schema, key, path):
    return get_schema_node(schema,  path.split("/")[1:], key)["type"]


class Config(MutableMapping):

    def __init__(self, config=None, schemas=None, temp_dir_node=("paths", "log_dir"),
                 delete_tmp_files=False, insertion_node=None, read_only=False):
        self.store: dict = dict()
        self.temp_dir_node = temp_dir_node
        self.delete_tmp_files = delete_tmp_files
        self.path = None
        self._tmp_file = None
        self._schemas: List[Schema] = []
        self._insertion_node = ()
        self._provenance = ConfigProv()
        self.read_only = read_only

        if schemas is not None:
            self.set_schemas(schemas)
        if config is not None:
            self.set_config(config, validate=False)
        if insertion_node is not None:
            self._insertion_node = insertion_node

        self.validate()

    def __del__(self):
        if self.delete_tmp_files and self._tmp_file is not None:
            os.remove(self._tmp_file.name)

    def __iadd__(self, other):
        merged_config = self._merge_configs_([self, other])
        self.store = merged_config.store
        self._schemas = merged_config.schemas
        self._insertion_node = merged_config._insertion_node
        self._provenance = merged_config.provenance
        return self

    def __add__(self, other):
        return self._merge_configs_([self, other])

    @property
    def provenance(self):
        return self._provenance

    @property
    def insertion_node(self):
        return self._insertion_node

    @insertion_node.setter
    def insertion_node(self, insertion_node):
        self._insertion_node = insertion_node

    @staticmethod
    def _merge_configs_(configs):
        return_config = Config()
        for config in configs:
            store = return_config
            if len(config.insertion_node):
                for key in config.insertion_node[:-1]:
                    if key not in store or store[key] is None:
                        store[key] = {}
                    store = store[key]
                key = config.insertion_node[-1]

                if key not in store:
                    store[key] = {}
                if isinstance(store[key], MutableMapping):
                    update(store[key], config)
                else:
                    store[key] = config.store.copy()
            else:
                update(store, config.store.copy())
            return_config.add_schemas(config.schemas)
        return_config.provenance.merging(configs)
        return return_config

    def add_schemas(self, schemas):
        def _check_schema_type_(schema_to_check):
            if isinstance(schema_to_check, (str, Path)):
                return Schema(schema_to_check)
            if isinstance(schema_to_check, Schema):
                return schema_to_check
            raise TypeError("schema must be a path to a schema file or a Schema object.")

        if isinstance(schemas, list):
            for schema in schemas:
                schema = _check_schema_type_(schema)
                if schema not in self._schemas:
                    self._schemas.append(schema)
        else:
            schema = _check_schema_type_(schemas)
            if schema not in self._schemas:
                self._schemas.append(schema)

    def set_schemas(self, schemas):
        self._schemas = []
        self.add_schemas(schemas)

    def set_config(self, config, schemas=None, validate=True):

        if isinstance(config, (str, Path)):
            self.path = Path(config)
            with Path(config).open('r') as check_stream:
                config = yaml.load(check_stream, Loader=ConfigMngLoader)
                if config is None:
                    return

        elif isinstance(config, Config):
            self.path = config.path
            self.temp_dir_node = config.temp_dir_node
            self.delete_tmp_files = config.delete_tmp_files
            self._tmp_file = config._tmp_file
            self._schemas = config.schemas
            self._insertion_node = config._insertion_node
            self._provenance = config.provenance
            self.read_only = config.read_only

        elif isinstance(config, dict):
            self.path = None

        else:
            raise TypeError("Received a configs object of an unrecognized type ({})."
                            .format(type(config)))

        if schemas is not None:
            self.set_schemas(schemas)

        self.update(config, validate=validate)

    @property
    def path(self) -> Path:
        return self._path

    def get_temporary_path(self):
        dir_ = None
        store = self.store.copy()
        for key in self.temp_dir_node:
            if key in store:
                store = store[key]
            else:
                store = None
                break
        if store is not None:
            assert(isinstance(store, str))
            dir_ = Path(store)
            try:
                dir_.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                warn("The path specified in your configuration file in ['path']['log_dir']" +
                     "(i.e., {}) does not exist and could not be created."
                     .format(self.store["paths"]["log_dir"]))
                dir_ = None

        self._tmp_file = NamedTemporaryFile(mode='w+b', prefix=".tmp_conf_", dir=dir_, suffix=".yaml")
        return Path(self._tmp_file.name)

    @path.setter
    def path(self, path: Path):
        if path is None:
            self._path = self.get_temporary_path()
        elif isinstance(path, str):
            self._path = Path(path)
        elif isinstance(path, Path):
            self._path = path
        else:
            raise TypeError("path must be of type str or Path if it is not None.")
        if not self._path.exists():
            raise FileNotFoundError("The configuration file {} was not found.".format(self._path))

    @property
    def schemas(self):
        return self._schemas

    @schemas.setter
    def schemas(self, schemas):
        self._schemas = schemas

    def validate(self, raise_exception=True, interactive=True):
        if len(self.schemas):
            if not self.path.exists():
                self.save()

            # kwalify supports using many schemas, where one is the main schema
            # and the other are partial schemas inserted in the main one. This
            # is not our use case; we have union of complete schema. Therefore,
            # we first merge ourselves our schemas.
            schema = Schema.merge_schemas(self.schemas)
            try:
                core = Core(source_file=str(self.path),
                            source_data={},
                            schema_file_obj=schema.schema_io)
                core.validate(raise_exception=raise_exception)
            except SchemaError:
                if interactive:
                    for error in core.errors:
                        self.manage_error(core, error)
                    self.validate(raise_exception, interactive)
                else:
                    print("An error has been raised while validating the configuration "
                          "against the schema. This exception is raised because the "
                          "interactive flag is set to False. To be asked interactively "
                          "to fill the values that are missing or incompatible with "
                          "the schema, use interactive=True. This should not be done "
                          "for the application level however. At this level, the schema "
                          "or the default configuration files should be corrected. " +
                          "Faulty config file: {}".format(self.path))
                    print("Config file {}:".format(str(self.path)))
                    with self.path.open("r") as f:
                        print(f.read())
                    print("Schema files:")
                    for schema in self.schemas:
                        with schema.path.open("r") as f:
                            print(f.read())
                    raise
            except:
                print("Unmanaged error while validating a configuration file. Faulty config file: {}".format(self.path))
                print("Config file {}:".format(str(self.path)))
                with self.path.open("r") as f:
                    print(f.read())
                print("Schema files:")
                for schema in self.schemas:
                    with schema.path.open("r") as f:
                        print(f.read())
                raise

    def set_value_at_path(self, value, key, path, silent_fail=False, only_if_key_in=False):
        self.provenance.propagate_changes(value, key, path)
        try:
            store = get_node(self.store, path)
            if only_if_key_in:
                if key in store:
                    store[key] = value
                else:
                    if not silent_fail:
                        raise KeyError
            else:
                store[key] = value
        except KeyError:
            if silent_fail:
                return
            raise

    def manage_error(self, core, error: SchemaError.SchemaErrorEntry):

        if "Cannot find required key" in error.msg:
            if get_schema_key_type(core.schema, error.key, error.path) == "map":
                value = {}
            else:
                value = input("The key {} at path {} of the ".format(error.key, error.path) +
                              "configuration file {} is missing.".format(self.path) +
                              " Please provide a value.")
            self.set_value_at_path(value, error.key, error.path.split("/")[1:])

        elif "does not match pattern" in error.msg:
            value = input("The value {} for the configuration key {}".format(error.value, error.path) +
                          " is not compatible with the pattern {}.".format(error.pattern) +
                          " required by the schema. Please provide a compatible value.")
            key = error.path.split("/")[-1]
            path = "/".join(error.path.split("/")[:-1])
            self.set_value_at_path(value, key, error.path.split("/")[1:])

        elif "is not of type" in error.msg:
            value = input("The type for value {} for the configuration key {}".format(error.value, error.path) +
                          " is not compatible with the type {}.".format(error.scalar_type) +
                          " required by the schema. Please provide a compatible value.")

            key = error.path.split("/")[-1]
            path = "/".join(error.path.split("/")[:-1])
            self.set_value_at_path(value, key, error.path.split("/")[1:])
        else:
            raise
        self.save()

    def __getitem__(self, key):
        try:
            return self.store[key]
        except KeyError:
            err_msg = "Key '{}' not found in this configuration.\n".format(key)
            # err_msg += "Configuration:\n {}\n".format(self.pretty_config())
            # err_msg += "Schemas:\n {}".format(self.schemas)
            print(err_msg)
            raise

    def __setitem__(self, key, value):
        self.store[key] = value

    def __delitem__(self, key):
        del self.store[key]

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)

    def __contains__(self, item):
        return item in self.store

    def __repr__(self):
        return str(self.to_json())

    def __str__(self):
        return json.dumps(self.to_json(), indent=4, sort_keys=True)

    def to_json(self):
        return {"config_path": str(self._path),
                "schema_paths": [str(schema.path) for schema in self._schemas],
                "config_dict": self.store}

    def pretty_config(self):
        return yaml.dump(self.store, default_flow_style=False, default_style='')

    def pretty_print(self):
        print(self.pretty_config())

    def update(self, *args, validate=True, **kwargs):
        if not args:
            raise TypeError("descriptor 'update' of 'Config' object "
                            "needs an argument")
        if len(args) > 1:
            raise TypeError('update expected at most 1 arguments, got {}'.format(len(args)))
        if args:
            update(self.store, args[0])
        update(self.store, kwargs)

        if validate:
            self.validate()

    def save(self, path=None):
        if path is None:
            if self.read_only:
                raise PermissionError("This configuration is in read-only mode. To save it, "
                                      "provide a path where to save a copy.")
        else:
            self.path = path

        with self.path.open("w") as stream:
            yaml.dump(self.store, stream, Dumper=Dumper)


ScalarConfigArg = typing.TypeVar('ScalarConfigArg', MutableMapping, str, Path, Config)
ConfigArg = typing.Union[ScalarConfigArg, typing.Iterable[ScalarConfigArg]]
