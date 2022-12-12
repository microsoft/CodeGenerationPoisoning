# coding=utf-8
"""ConfigDict class reads yaml config files and presents a dict() get/set API to read configs."""
# pylint: disable=too-many-public-methods


import copy
import logging
import os.path
import re
import sys

import six
import yaml

import dsi.common.whereami as whereami

LOG = logging.getLogger(__name__)


class ConfigDict(dict):
    """Get/Set API for DSI (Distributed Performance 2.0) config files (dsi/docs/).

    A ConfigDict class will read a multitude of yaml configuration files, and present
    them as a single python dictionary from where keys can be read, and some keys can also
    be set and ultimately written to a module_name.out.yml file.

    The value returned for a given key, say config['module_name']['key']['subkey'] is
    actually the result of overlaying several yaml files into what only seems to be a
    standard dictionary. The returned value is found in the various files in the following
    priority:

    overrides.yml
    module_name.yml
    defaults.yml
    raise KeyError"""

    modules = [
        # These are in the order in which they are used
        "bootstrap",
        "runtime",
        "runtime_secret",
        "infrastructure_provisioning",
        "workload_setup",
        "mongodb_setup",
        "test_control",
        "analysis",
        "_internal",
    ]

    def __init__(self, which_module_am_i, config_root=None):
        self.raw = {}
        """The dictionary wrapped by this ConfigDict. When you access["sub"]["keys"], this contains
        the substructure as well."""

        self.defaults = {}
        """The dictionary holding defaults, set in dsi/configurations/defaults.yml.

        If neither raw nor overrides specified a value for a key, the default value is returned from
        here."""

        self.overrides = {}
        """The dictionary holding contents of the *.override.yml files.

        Leaf values from overrides are "upserted" onto the values in raw during __getitem__()."""

        self.root = None
        """The complete config dictionary.

        Initially this is equal to self, but then stays at the same root forever.
        This is used to substitute ${variable.references}, which can point anywhere into the config,
        not just the sub-structure currently held in self.raw."""

        self.path = []
        """When descending to sub keys, this is the current path from root.

        Used in __setitem__() to set the value into the root dictionary.
        Also checked to see if we're at the path of a mongod/mongos/configsvr config_file."""

        super(ConfigDict, self).__init__()
        self.assert_valid_module(which_module_am_i)
        self.module = which_module_am_i
        self.root = self
        self.config_root = os.getcwd() if config_root is None else config_root

    def load(self):
        """
        Populate with contents of module_name.yml, module_name.out.yml, overrides.yml.

        Note: exceptions may be raised by the lower layer, see :method:
        `ConfigDict.assert_valid_ids`, `_yaml_load`.
        """
        loaded_files = []
        # defaults.yml
        file_name = whereami.dsi_repo_path("configurations", "defaults.yml")
        with open(file_name) as file_handle:
            self.defaults = _yaml_load(file_handle, file_name)
            loaded_files.append(file_name)

        # All module_name.yml and module_name.out.yml
        for module_name in self.modules:
            file_name = os.path.join(self.config_root, module_name + ".yml")
            if os.path.isfile(file_name):
                with open(file_name) as file_handle:
                    self.raw[module_name] = _yaml_load(file_handle, file_name)
                    loaded_files.append(file_name)
            elif module_name != "_internal":
                # Allow code to assume that first level of keys always exists
                self.raw[module_name] = {}
            file_name = os.path.join(self.config_root, module_name + ".out.yml")
            if os.path.isfile(file_name):
                with open(file_name) as file_handle:
                    # Note: The .out.yml files will add a single key: ['module_name']['out']
                    out = _yaml_load(file_handle, file_name)
                    if isinstance(out, dict):
                        if module_name in self.raw:
                            self.raw[module_name].update(out)
                        else:
                            self.raw.update({module_name: out})
                            loaded_files.append(file_name)

        # overrides.yml
        file_name = os.path.join(self.config_root, "overrides.yml")
        if os.path.isfile(file_name):
            file_handle = open(file_name)
            self.overrides = _yaml_load(file_handle, file_name)
            file_handle.close()
            loaded_files.append(file_name)

        LOG.info("Loaded DSI config files: %s", loaded_files)
        self.assert_valid_ids()

        return self

    def save(self):
        """Write contents of self.raw[self.module]['out'] to module_name.out.yml"""
        file_name = os.path.join(self.config_root, self.module + ".out.yml")
        file_handle = open(file_name, "w")
        out = {"out": self.raw[self.module]["out"]}
        # yaml.safe_dump() handles unicode strings as if they were normal text. As they are!
        file_handle.write(yaml.safe_dump(out, default_flow_style=False))
        file_handle.close()
        LOG.info("ConfigDict: Wrote file: %s", file_name)

    def assert_valid_module(self, module_name):
        """Check that module_name is one of Distributed Performance 2.0 modules, or _internal."""
        if module_name not in self.modules:
            raise ValueError("This is not a valid DSI module: " + module_name)

    def assert_valid_ids(self):
        """
        Check that ids in this config file are allowed and unique.

        :raises InvalidConfigurationException if id values are invalid.
        """
        errs = []
        self[self.module].find_and_validate_ids(errs=errs)
        if errs:
            raise InvalidConfigurationException(errs)

    def find_and_validate_ids(self, seen_ids=None, path=None, errs=None):
        """
        Recursively find and validate that all ids are allowed and unique.
        This is used to validate the ConfigDict instance dynamically. Most importantly, this is
        called after variable references are expanded in `ConfigDict.load`.

        :param set seen_ids: Id values seen so far in the traversal.
        :param list path: Key path we took to get to the current id.
        :param list errs: Errors seen so far.
        """
        if seen_ids is None:
            seen_ids = set()
        if path is None:
            path = []
        if errs is None:
            errs = []

        for key in self.keys():
            # ConfigDict is late binding. It's ok if some variable references throw ValueError
            # at load time. Only if user tries to access them specifically, will the user then
            # get the ValueError.
            try:
                value = self[key]
            except ValueError:
                # Note that not asserting anything is ok. If user tried to do something with this
                # key, they will likewise get a ValueError.
                continue

            if key == "id":
                validate_id(value, path, seen_ids, errs, self.module)
            else:
                if isinstance(value, ConfigDict):
                    value.find_and_validate_ids(seen_ids, path, errs)
                elif isinstance(value, list):
                    for elem in self.find_nested_config_dicts(value):
                        elem.find_and_validate_ids(seen_ids, path, errs)

    def find_nested_config_dicts(self, obj):
        """
        Finds and returns the ConfigDict objects nested within an object.

        :param object obj: Object to find ConfigDicts in.
        :return: List of nested ConfigDict objects.
        """
        config_dicts = []
        if isinstance(obj, ConfigDict):
            return [obj]
        if isinstance(obj, list):
            for elem in obj:
                config_dicts.extend(self.find_nested_config_dicts(elem))

        return config_dicts

    def lookup_path(self, path):
        """ lookup the path. This is a convenience method for converting
        'a.path.0.like.this' to self['a']['path'][0]['like']['this'].
        Note the conversion of the str '0' to  int 0. This is expected behaviour,
        all integers in the path are treated this way.
        Additionally, 'a.path.-1.like.this' will be converted to the following
        equivalent call self['a']['path'][-1]['like']['this']

        :param path str the name to lookup, it is of the form of 'a.path.0.like.this'.

        :returns object the value at the path
        :raises KeyError if the key or portion of the path does not exist. The
        key error should reflect the level at which the unaliased name failed.


        """

        path = self.variable_path_as_list(path)

        current = self
        keys = ()
        for key in path:
            keys += (str(key),)
            try:
                current = current[key]
            except TypeError:
                raise KeyError(
                    "ConfigDict: Key not found: {} in path {}".format(".".join(keys), path)
                )
            except KeyError:
                raise KeyError(
                    "ConfigDict: Key not found: {} in path {}".format(".".join(keys), path)
                )
            except IndexError:
                raise KeyError(
                    "ConfigDict: list index out of range: {} in path {}".format(
                        ".".join(keys), path
                    )
                )

        return current

    # Implementation of dict API

    def __repr__(self):
        str_representation = "{"
        i = 0
        for key in self.keys():
            if i > 0:
                str_representation += ", "
            if isinstance(key, six.string_types):
                str_representation += "'" + key + "': "
            else:
                str_representation += str(key) + ": "
            if isinstance(self[key], six.string_types):
                str_representation += "'" + str(self[key]) + "'"
            else:
                str_representation += str(self[key])
            i += 1
        str_representation += "}"
        return str_representation

    def __contains__(self, key):
        return key in list(self.keys())

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def keys(self):
        """Return list of keys, taking into account overrides."""
        raw_keys = set()
        overrides_keys = set()
        defaults_keys = set()
        # Magic key: In a mongodb_setup.topology, if this is a mongod/mongos/configsvr node
        # always return a config_file key.
        config_file_key = {"config_file"} if self.is_topology_node() else set()
        rs_conf_key = {"rs_conf"} if self.is_topology_replset() else set()
        if isinstance(self.raw, dict):
            raw_keys = set(self.raw.keys())
        if isinstance(self.overrides, dict):
            overrides_keys = set(self.overrides.keys())
        if isinstance(self.defaults, dict):
            defaults_keys = set(self.defaults.keys())
        return list(raw_keys | overrides_keys | defaults_keys | config_file_key | rs_conf_key)

    def items(self):
        for val in list(self.iteritems()):
            yield val

    def iteritems(self):
        """Iterator over the key, values"""
        return iter((key, self[key]) for key in self.keys())

    def iterkeys(self):
        """Iterator over the keys"""
        return iter(self.keys())

    def itervalues(self):
        """Iterator over the values"""
        return iter(self.values())

    # pylint: disable=line-too-long
    # TODO: __iter__ isn't actually called if you do dict(instance_of_ConfigDict), so casting to dict doesn't work.
    # See http://stackoverflow.com/questions/18317905/overloaded-iter-is-bypassed-when-deriving-from-dict
    def __iter__(self):
        """Iterator over the keys"""
        return six.iterkeys(self)

    def values(self):
        """Return list of values, taking into account overrides."""
        return [self[key] for key in self.keys()]

    def __getitem__(self, key):
        """Return dict item, after applying overrides and ${variable.references}"""
        try:
            value = self.descend_key_and_apply_overrides(key)
            value = self.variable_references(key, value)
        except KeyError:
            raise KeyError("Key or sub-key not found: [{}] at path [{}]".format(key, self.path))
        return value

    def __setitem__(self, key, value):
        _check_object({key: value})
        self.assert_writeable_path(key)
        self.raw[key] = value
        # Set the same element in self.root (this is the one that sticks)
        to_set = self.root.raw
        for element in self.path:
            to_set = to_set[element]
        to_set[key] = value

    def as_dict(self):
        # pylint: disable=line-too-long
        """Cast this DictConfig into a normal dict.

        Note that this is a supplement solution until we fix the issues arising from subclassing
        from dict / not being able to cast normally with dict(config).
        http://stackoverflow.com/questions/18317905/overloaded-iter-is-bypassed-when-deriving-from-dict
        """
        return copy_obj(self)

    # __getitem__() helpers
    def descend_key_and_apply_overrides(self, key):
        """Return the key, but (for leaf nodes) if an override exists, return the override value.

           The twist is that override can exist but be None (such as an empty list element), in
           which case we still return the value from raw. (It's not possible to delete a value,
           or set to None, with override.)

           If no value exist, see if a default value exists.
           """
        # Check the magic per node mongod_config/mongos_config/configsvr_config keys first.
        # Note to reader: on first time, skip this, then come back to this when you understand
        # everything else first.
        value, key_exists = self.get_node_mongo_config(key)
        if key_exists:
            return value

        # For leaf nodes, check overrides and return it if specified
        if (
            self.overrides
            and isinstance(self.overrides, dict)
            and (
                not isinstance(self.raw.get(key, "some string"), (list, dict))
                or (key in self.overrides and self.overrides.get(key) is None)
            )
        ):
            value = self.overrides.get(key)
            key_exists = key_exists or key in self.overrides

        # And if none of the above apply, we just get the value from the raw dict, or from defaults:
        if not key_exists:
            value = self.raw.get(key)
            key_exists = key_exists or key in self.raw
        if not key_exists and isinstance(self.defaults, dict):
            value = self.defaults.get(key)
            key_exists = key_exists or key in self.defaults
        # We raise our own error to highlight that key really is missing, not a bug or anything.
        if not key_exists:
            raise KeyError("ConfigDict: Key not found: {}".format(key))

        value = self.wrap_dict_as_config_dict(key, value)

        # While descending a dict, keep the same subtree of overrides.
        # For a leaf node, the override is already applied.
        # For a list, either of the above applies to the list elements.
        if isinstance(value, ConfigDict):
            # value.overrides is already set if we're returning from get_node_mongo_config().
            # If so, keep it.
            if not value.overrides and isinstance(self.overrides, dict):
                value.overrides = self.overrides.get(key, {})

        return value

    def wrap_dict_as_config_dict(self, key, value):
        """If item to return is a dict, return a ConfigDict, otherwise return as is.

        This is to keep the ConfigDict behavior when descending into the dictionary
        like conf['mongodb_setup']['mongos_config']...
        """
        if isinstance(value, dict):
            return_dict = ConfigDict(self.module)
            return_dict.raw = value
            if isinstance(self.defaults, dict):
                return_dict.defaults = self.defaults.get(key, {})
            return_dict.root = self.root
            # copy list (by value) and append the newest key
            return_dict.path = list(self.path)
            return_dict.path.append(key)
            return return_dict
        if isinstance(value, list):
            return_list = []
            for listvalue in value:
                child = self.wrap_dict_as_config_dict(key, listvalue)
                if isinstance(child, ConfigDict):
                    # Store list index as part of the path for the elements in this list
                    child.path.append(len(return_list))
                return_list.append(child)
            return return_list
        return value

    def variable_references(self, key, value):
        """
        For any ConfigDict item that needs to be referenced, substitute ${module.item}.

        In any ConfigDict module, a reference can be made to an item in another ConfigDict module,
        including that module itself. These references can also be recursive. For example,
        `${mongodb_setup.authetication.${boostrap.authentication}.mongodb_url}` can expand out to
        `${monogdb_setup.authentication.disabled.mongodb_url}` and then, finally, to
        `mongodb://${mongodb_setup.meta.hosts}/admin`.
        """
        # This while loop resolves recursive references until all are taken care of.
        # Example: ${a.${foo}.c} (where foo: b)
        while True:
            # Expand variable references in a list also.
            # Note: This approach imposes a requirement that all ${variable.references}
            # in all elements of the list must successfully evaluate to a value,
            # not just the element(s) the user is about to access.
            if isinstance(value, list):
                return [
                    self.variable_references(index, list_value)
                    for index, list_value in enumerate(value)
                ]

            # str and unicode strings have the common parent class basestring.
            if not isinstance(value, six.string_types):
                break

            values = []
            # regex matches the innermost { } pairs, and returns the inside content of those.
            matches = re.findall(r"\$\{([^\{]*?)\}", value)
            if not matches:
                break

            for path in matches:
                # Note that because self.root is itself a ConfigDict, if a referenced
                # value would itself contain a ${variable.reference}, then it will
                # automatically be substituted too.
                # For example, in docs/config-specs/*.yml we have:
                # mongodb_setup.meta.hosts ->
                # mongodb_setup.topology.0.mongos.0.private_ip ->
                # infrastructure_provisioning.out.mongos.0.private_ip
                # and that resolves correctly via recursion.
                try:
                    values.append(self.root.lookup_path(path))
                except:
                    path_from_root = copy.copy(self.path)
                    path_from_root.append(key)
                    raise ValueError(
                        f"ConfigDict error at {path_from_root}: Cannot resolve variable "
                        f"reference '{path}', error at '{path}': {sys.exc_info()[0]} {sys.exc_info()[1]}"
                    )
            between_values = re.split(r"\$\{[^\{]*?\}", value)

            # If the variable reference is the entire value, then return the referenced value as it
            # is, including preserving type. Otherwise, concatenate back into a string.
            if len(between_values) == 2 and between_values[0] == "" and between_values[1] == "":
                value = values[0]
            else:
                value = between_values.pop(0)
                while values:
                    value += str(values.pop(0))
                    value += between_values.pop(0)

        return value

    def variable_path_as_list(self, path):
        """Split path.like.0.this into parts and return the list."""
        # pylint: disable=no-self-use

        parts = path.split(".")
        # If an element in the path converts to integer, do so
        for i, element in enumerate(parts):
            if is_integer(element):
                parts[i] = int(element)
        return parts

    def get_node_mongo_config(self, key):
        """If key is a config_file key for a node in a mongodb_setup.topology

           we need to magically return the common mongod/s_config merged with contents of this key.
           Some non-default options like fork are needed for anything to work. The below code will
           not raise exception if no config exists.

           This function does a similar merge for the rs_conf value for replsets."""
        # pylint: disable=too-many-boolean-expressions

        if self.is_topology_node() and key == "config_file":
            # Note: In the below 2 lines, overrides and ${variables} are already applied
            common_config = self.root["mongodb_setup"].get(
                self.topology_node_type() + "_config_file"
            )
            node_specific_config = self.raw.get(key, {})
            return self.get_merged_config_dict_value(common_config, node_specific_config, key), True

        if self.is_topology_replset() and key == "rs_conf":
            # Note: In the below 2 lines, overrides and ${variables} are already applied
            common_rs_conf = self.root["mongodb_setup"].get("rs_conf")
            replset_rs_conf = self.raw.get("rs_conf", {})
            return self.get_merged_config_dict_value(common_rs_conf, replset_rs_conf, key), True

        return None, False

    @staticmethod
    def get_merged_config_dict_value(config_dict1, config_dict2, key):
        """Merge config_dict1[key] and config_dict2[key] into a single ConfigDict object."""
        # Technically this works the same as if config_dict1 was the raw value
        # and config_dict2 is a dict with overrides. So let's reuse some code...
        helper = ConfigDict("_internal")
        helper.raw = {key: config_dict1}
        helper.overrides = {key: config_dict2}
        return helper[key]

    def is_topology_node(self):
        """
        Returns true if self.path is a mongod/s/configsvr node under mongodb_setup.topology.

        Note: We cannot call self['cluster_type'] or self.get('cluster_type') in this function, as
        that would cause recursion. This causes a small restriction on defining topologies in the
        Yaml files: For a standalone node, the 'cluster_type' value must be a literal word, it
        cannot be a ${variable.reference}. It can however be defined in any of defaults.yml,
        mongodb_setup.yml or overrides.yml.
        """
        # pylint: disable=too-many-boolean-expressions
        # Standalone nodes have a different path
        if (
            len(self.path) >= 3
            and self.path[0] == "mongodb_setup"
            and self.path[1] == "topology"
            and isinstance(self.path[2], int)
            and (
                (isinstance(self.raw, dict) and self.raw.get("cluster_type") == "standalone")
                or (
                    isinstance(self.defaults, dict)
                    and self.defaults.get("cluster_type") == "standalone"
                )
                or (
                    isinstance(self.overrides, dict)
                    and self.overrides.get("cluster_type") == "standalone"
                )
            )
        ):
            return True

        # replset and sharded_cluster topologies
        if (
            len(self.path) >= 3
            and self.path[0] == "mongodb_setup"
            and self.path[1] == "topology"
            and isinstance(self.path[2], int)
            and self.path[-2] in ("mongod", "mongos", "configsvr")
            and isinstance(self.path[-1], int)
        ):
            return True

        return False

    def topology_node_type(self):
        """Return one of mongod, mongos or configsvr by looking upwards in self.path

        Note: This only works when called from get_node_mongo_config(). We don't guard against
        random results if calling it from elsewhere."""
        if self.path[-2] in ("mongod", "mongos", "configsvr"):
            return self.path[-2]
        if is_integer(self.path[-1]):
            return "mongod"
        return None

    def is_topology_replset(self):
        """Returns true if self.path is a cluster_type: replset node under mongodb_setup.topology.

        Note: We cannot call self['cluster_type'] or self.get('cluster_type') in this function, as
        that would cause recursion. This causes a small restriction on defining topologies in the
        Yaml files: For a standalone node, the 'cluster_type' value must be a literal word, it
        cannot be a ${variable.reference}. It can however be defined in any of defaults.yml,
        mongodb_setup.yml or overrides.yml."""
        # pylint: disable=too-many-boolean-expressions
        # replset and sharded_cluster topologies
        if (
            len(self.path) >= 3
            and self.path[0] == "mongodb_setup"
            and self.path[1] == "topology"
            and isinstance(self.path[2], int)
            and (
                (isinstance(self.raw, dict) and self.raw.get("cluster_type") == "replset")
                or (
                    isinstance(self.defaults, dict)
                    and self.defaults.get("cluster_type") == "replset"
                )
                or (
                    isinstance(self.overrides, dict)
                    and self.overrides.get("cluster_type") == "replset"
                )
            )
        ):
            return True

        return False

    ### __setitem__() helpers
    def assert_writeable_path(self, key):
        """ConfigDict is read-only, except for self[self.module]['out'] namespace."""
        if len(self.path) >= 2 and self.path[0] == self.module and self.path[1] == "out":
            return True
        if len(self.path) == 1 and self.path[0] == self.module and key == "out":
            return True
        raise KeyError(
            'Only values under self["' + self.module + '"]["out"] are settable in this object'
        )


def copy_obj(obj):
    """Return a copy of the dictionary or list. For a ConfigDict(), return plain dict()."""
    if isinstance(obj, dict):
        new_dict = {}
        for key in obj.keys():
            new_dict[key] = copy_obj(obj[key])
        return new_dict
    if isinstance(obj, list):
        return [copy_obj(item) for item in obj]
    return obj


def is_integer(astring):
    """Return True if astring is an integer, false otherwise."""
    try:
        int(astring)
        return True
    except ValueError:
        return False


def change_key_name(dictionary, old_key, new_key):
    """Change key names at top level of a dictionary"""
    for key, val in six.iteritems(dictionary):
        if key == old_key:
            dictionary[new_key] = val
            del dictionary[old_key]


def is_reserved_word(word):
    """
    Return True if given word is reserved.

    :param str word: Word to match against resrved strings.
    :return: True if the word is reserved, False otherwise
    """
    return word in _RESERVED_WORDS or _RESERVED_REX.match(word)


def validate_id(value, path, ids, errs, src_file):
    """
    Check that id field is not reserved and is unique in this file.

    :param str value: Value to validate.
    :param list path: Key path we took to get to value.
    :param set ids: Id values that have already been seen in this traversal.
    :param list errs: Any errors we've seen so far - modifies this as an "out" parameter.
    :param str src_file: Source file name.
    """

    if not isinstance(value, six.string_types):
        errs.append(
            {
                "err_type": "Invalid Id Type",
                "src_file": src_file,
                "item": value,
                "item_type": type(value),
                "path": copy.deepcopy(path),
            }
        )
    else:
        # check reserved words
        if is_reserved_word(value):
            errs.append(
                {
                    "err_type": "Id is Reserved",
                    "src_file": src_file,
                    "item": value,
                    "item_type": type(value),
                    "path": copy.deepcopy(path),
                }
            )

        # check uniqueness
        if value in ids:
            errs.append(
                {
                    "err_type": "Duplicate Id",
                    "src_file": src_file,
                    "item": value,
                    "item_type": type(value),
                    "path": copy.deepcopy(path),
                }
            )
        else:
            ids.add(value)


class InvalidConfigurationException(Exception):
    """Indicates invalid configuration either from YAML or from user modifying 'out' config."""

    def __init__(self, errors):
        self.errors = errors
        key_info = "Keys must be strings and match {}.".format(_VALID_KEY_REX_SRC)
        value_info = "Values must be of type {}.".format(
            list((it.__name__ for it in _VALID_SCALAR_TYPES))
        )
        id_info = "Id fields must be unique in a file and cannot be reserved words."
        errs = ", ".join(
            [
                "😱 {} [{}] of type [{}] at path [{}] in file [{}]".format(
                    err["err_type"],
                    err["item"],
                    err["item_type"].__name__,
                    ".".join(str(p) for p in err["path"]),
                    err["src_file"],
                )
                for err in self.errors
            ]
        )
        message = " ".join([key_info, value_info, id_info, errs])
        super(InvalidConfigurationException, self).__init__(message)


def _yaml_load(handle, path):
    """
    Load yaml and check that the object's types and keys are valid.
    :param handle: file io stream from which to read
    :return: parsed and checked object
    :raises InvalidConfigurationException if keys or types are invalid
    """
    loaded = yaml.safe_load(handle)
    _check_object(loaded, path)
    return loaded


_VALID_KEY_REX_SRC = r"^[A-Za-z][A-Za-z0-9\-_]*$"
"""All ConfigDict keys must match this regex."""
# Create a separate object since str() of a compiled regex doesn't give you the text.
_VALID_KEY_REX = re.compile(_VALID_KEY_REX_SRC)
"""Compiled version of `_VALID_KEY_REX_SRC`"""
# pylint: disable=invalid-name
_VALID_KEY_TYPES = six.string_types
"""All ConfigDict keys must be one of these types."""

_VALID_SCALAR_TYPES = tuple(list(six.string_types) + [float, int, type(None)])
"""All ConfigDict values must be one of these or list/dict (recursive) types"""

# Words matching /on_.*/ as well as those enumerated below (in alphabetical order) are reserved in
# config files. Use is_reserved_word to test if a word is reserved.
_RESERVED_REX = re.compile(r"on_.*")

_RESERVED_WORDS = [
    "between_tests",
    "post_cluster_restart",
    "post_cluster_start",
    "post_cluster_stop",
    "post_task",
    "post_test",
    "pre_cluster_restart",
    "pre_cluster_start",
    "pre_cluster_stop",
    "pre_task",
    "pre_test",
    "workload_setup",
    "upon_error",
]


def _check_object(obj, src_file=None):
    """
    Validates yaml objects prior to variable expansion and translation into a ConfigDict object.
    Called through `_yaml_load` in `_main_` (used in lint-yaml.sh) for static validity checks. Also
    used during ConfigDict loading and update (`__setitem__`).

    :param obj: object to check for validity as use as a ConfigDict entry.
    :raises InvalidConfigurationExcetion if keys or types are insuitable.
    """

    def explore(obj, path, ids, errs):
        """
        :param obj: object (scalar or complex type) we're traversing
        :param path: key path we took to get to obj
        e.g. `{foo:{bar:1}` would result in path of [foo,bar] when obj=1
        :param ids: id values that have already been seen in this traversal
        :param errs: any errors we've seen so far. modifies this as an "out" parameter
        """
        if isinstance(obj, dict):
            for key in obj.keys():
                path.append(key)
                if not isinstance(key, _VALID_KEY_TYPES) or not _VALID_KEY_REX.match(key):
                    errs.append(
                        {
                            "err_type": "Invalid Key",
                            "src_file": src_file,
                            "item": key,
                            "item_type": type(key),
                            "path": copy.deepcopy(path),
                        }
                    )
                if key == "id":
                    validate_id(obj[key], path, ids, errs, src_file)
                explore(obj[key], path, ids, errs)
                path.pop()
        elif isinstance(obj, list):
            index = 0
            for item in iter(obj):
                path.append(index)
                explore(item, path, ids, errs)
                path.pop()
                index = index + 1
        elif not isinstance(obj, _VALID_SCALAR_TYPES):
            errs.append(
                {
                    "err_type": "Invalid Value Type",
                    "src_file": src_file,
                    "item": obj,
                    "item_type": type(obj),
                    "path": copy.deepcopy(path),
                }
            )

    path = []
    ids = set()
    errs = []
    explore(obj, path, ids, errs)
    if errs:
        raise InvalidConfigurationException(errs)


if __name__ == "__main__":
    with open(sys.argv[1], "r") as w:
        print("CHECKING {}".format(sys.argv[1]))
        _yaml_load(w, sys.argv[1])
        print("OKAY {}".format(sys.argv[1]))
