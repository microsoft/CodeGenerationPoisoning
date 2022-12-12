from pathlib import Path
import typing
import json
import io
from copy import copy, deepcopy
from warnings import warn
from typing import List
from collections.abc import MutableMapping, Mapping, MutableSequence

import yaml
try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

from .utils import ConfigMngLoader, eq_mappable, get_node, pretty_print
from .exceptions import NotMergeable, UndefinedScalarMerging, MappingNonMappingMerging, \
    MatchingRuleViolation, UndefinedSequenceMerging


string_io_path = Path("<StringIO>")


class ShadowBehavior:
    def __init__(self):

        """ If equals to "last_dominate", when scalar values are present for
            equivalent nodes in more than one schema, the value from the last
            schema to be merged is retained. If it is equals to "first_dominate"
            the value of the first is retained. If equal to "raise", a
            a NotMergeable exception is raised. If equal to "identical", will take
            either values if they are identical, else will raise an exception.
        """
        self.default_shadow_dominance = "last_dominate"

        self.sequence_shadow_dominance = "unique_right_extend_left"

        self.rules = {
            "name": "concatenate",
            "type": "identical",
            "required": "conservative",
            "matching": "permissive",
            "matching-rule": "permissive",
            "pattern": "permissive",
            "allowempty": "permissive"
        }

        self.rules_choices = {
            "name": ["concatenate", "left_dominate", "right_dominate"],
            "type": ["identical"],
            "required": ["conservative", "permissive", "identical"],
            "matching": ["conservative", "permissive", "identical"],
            "matching-rule": ["conservative", "permissive", "identical"],
            "pattern": ["conservative", "permissive", "identical"],
            "allowempty": ["conservative", "permissive", "identical"],
        }

        aliases = [("req", "required")]
        for alias, aliased in aliases:
            self.rules[alias] = self.rules[aliased]
            self.rules_choices[alias] = self.rules_choices[aliased]

    def merge_sequences(self, value1, value2, key):
        if self.sequence_shadow_dominance == "unique_right_extend_left":
            ret_val = copy(value1)
            ret_val.extend([item for item in value2 if item not in value1])
            return ret_val
        if self.sequence_shadow_dominance == "unique_right_extend_left":
            ret_val = copy(value2)
            ret_val.extend([item for item in value1 if item not in value2])
            return ret_val
        if self.sequence_shadow_dominance == "right_extend_left":
            ret_val = copy(value1)
            ret_val.extend(value2)
            return ret_val
        if self.sequence_shadow_dominance == "right_extend_left":
            ret_val = copy(value2)
            ret_val.extend(value1)
            return ret_val
        if self.sequence_shadow_dominance == "last_dominate":
            return value2
        if self.sequence_shadow_dominance == "first_dominate":
            return value1
        if self.sequence_shadow_dominance == "identical":
            if value1 == value2:
                return value1
            raise MatchingRuleViolation("Values for the '{}' key for corresponding nodes ".format(key) +
                                        "must be identical.")
        if self.sequence_shadow_dominance == "raise":
            raise NotMergeable("Values {} and {} cannot be merged for key {}."
                               .format(value1, value2, key))
        raise ValueError("ShadowBehavior.default_shadow_dominance can only take" +
                         "'last_dominate', 'first_dominate', or 'raise' as value." +
                         "It has been set to '{}'.".format(self.sequence_shadow_dominance))

    def merge_scalars(self, value1, value2, key):
        def raise_error():
            raise ValueError("ShadowBehavior.rules['{}'] can only take".format(key) +
                             "values in {}. ".format(self.rules_choices[key]) +
                             "It has been set to '{}'.".format(self.rules[key]))

        def check_rule_identical():
            if value1 == value2:
                return value1
            raise MatchingRuleViolation("Values for the '{}' key for corresponding nodes ".format(key) +
                                        "must be identical.")

        if key == "name":
            if self.rules[key] == "concatenate":
                return "{}_{}".format(value1, value2)
            if self.rules[key] == "left_dominate":
                return value1
            if self.rules[key] == "right_dominate":
                return value2
            raise_error()

        if key == "type":
            if self.rules[key] == "identical":
                return check_rule_identical()
            raise_error()

        if key == "required":
            if self.rules[key] == "conservative":
                return value1 and value2
            if self.rules[key] == "permissive":
                return value1 or value2
            if self.rules[key] == "identical":
                return check_rule_identical()
            raise_error()

        if key == "matching":
            if self.rules[key] == "conservative":
                if value1 == "all" or value2 == "all":
                    return "all"
                if value1 == "any" or value2 == "any":
                    return "any"
                return "*"
            if self.rules[key] == "permissive":
                if value1 == "*" or value2 == "*":
                    return "*"
                if value1 == "any" or value2 == "any":
                    return "any"
                return "all"
            if self.rules[key] == "identical":
                return check_rule_identical()
            raise_error()

        if key == "matching-rule":
            if self.rules[key] == "conservative":
                if value1 == "all" or value2 == "all":
                    return "all"
                return "any"
            if self.rules[key] == "permissive":
                if value1 == "any" or value2 == "any":
                    return "any"
                return "all"
            if self.rules[key] == "identical":
                return check_rule_identical()
            raise_error()

        if key == "pattern":
            if self.rules[key] == "conservative":  # union
                return "({})|({})".format(value1, value2)
            if self.rules[key] == "permissive":  # intersection
                return "^(?={}$)(?={}$)".format(value1, value2)
            if self.rules[key] == "identical":
                return check_rule_identical()
            raise_error()

        if key == "allowempty":
            if self.rules[key] == "conservative":
                return value1 or value2
            if self.rules[key] == "permissive":
                return value1 and value2
            if self.rules[key] == "identical":
                return check_rule_identical()
            raise_error()

        if self.default_shadow_dominance == "last_dominate":
            return value2
        if self.default_shadow_dominance == "first_dominate":
            return value1
        if self.default_shadow_dominance == "identical":
            return check_rule_identical()
        if self.default_shadow_dominance == "raise":
            raise NotMergeable("Values {} and {} cannot be merged for key {}."
                               .format(value1, value2, key))
        raise ValueError("ShadowBehavior.default_shadow_dominance can only take" +
                         "'last_dominate', 'first_dominate', or 'raise' as value." +
                         "It has been set to '{}'.".format(self.default_shadow_dominance))


class Schema:

    def __init__(self, schema: "SchemaArg", insertion_node=()):

        if isinstance(schema, list):
            merged_schema = self.merge_schemas(schema)
            self._path = merged_schema.path
            self._schema_io = merged_schema.schema_io
            self._insertion_node = merged_schema.insertion_node
            return

        if isinstance(schema, io.StringIO):
            self._path = string_io_path
            try:
                yaml.load(schema.read(), Loader=ConfigMngLoader)
                schema.seek(0)
            except:
                print("Invalid YAML file.")
            self._schema_io = schema
            self._insertion_node = insertion_node
            return

        if isinstance(schema, MutableMapping):
            self._path = string_io_path
            self._schema_io = io.StringIO(yaml.dump(schema, indent=4, sort_keys=True, Dumper=Dumper))
            self._insertion_node = insertion_node
            return

        if isinstance(schema, (str, Path)):
            self._path: Path = Path(schema)
            self._schema_io: typing.Optional[io.StringIO] = None
            self._insertion_node: typing.Sequence[str] = insertion_node

            if not self._path.exists():
                raise FileNotFoundError("The schema file {} was not found.".format(self._path))
            return

        raise TypeError("schema must be a str, a Path object pointing to a schema file, " +
                        "a MutableMapping describing the schema, or a list of Schema objects." +
                        "Received type: {}".format(type(schema)))

    @property
    def insertion_node(self):
        return self._insertion_node

    @insertion_node.setter
    def insertion_node(self, insertion_node):
        if isinstance(insertion_node, str):
            insertion_node = [insertion_node]
        self._insertion_node = insertion_node

    @property
    def path(self) -> Path:
        return self._path

    def set(self, node, value):
        if not isinstance(node, MutableSequence):
            node = [node]
        schema_data = self.load()
        if len(node) == 1:
            schema_data[node[0]] = value
        else:
            get_node(schema_data, node[:-1])[node[-1]] = value
        self._path = string_io_path
        self._schema_io = io.StringIO(yaml.dump(schema_data, indent=4, sort_keys=True, Dumper=Dumper))

    def __eq__(self, other):
        if self.path != string_io_path and other.path != string_io_path:
            return (self._path == other.path and
                    self.insertion_node == other.insertion_node)
        else:
            return self.eq_schema_io(other)


    def eq_schema_io(self, other: "Schema"):
        return eq_mappable(self.load(), other.load())

    def pretty_print(self):
        pretty_print(self.load())

    def to_json(self):
        return {"path": str(self._path),
                "insertion_node": self._insertion_node}

    def __repr__(self):
        return str(self.to_json())

    def __str__(self):
        return json.dumps(self.to_json(), indent=4, sort_keys=True)

    def __add__(self, other):
        return Schema.merge_schemas([self, other])

    def __iadd__(self, other):
        merged_schema = self.merge_schemas([self, other])
        self._path = merged_schema._path
        self._schema_io = merged_schema._schema_io
        self._insertion_node = merged_schema._insertion_node
        return self

    @staticmethod
    def merge_schemas(schemas: List["Schema"],
                      name: typing.Optional[str] = None,
                      shadow_behavior: typing.Optional[ShadowBehavior] = None) -> "Schema":
        """
        :param schemas: List of Schema objects that are to be merged.
        :param name: Name for schema resulting from the merging operation.
        :param shadow_behavior: ShadowBehavior defining what values will
                                get shadowed by the other is defined by the
                                ShadowBehavior passed. If None, ShadowBehavior() will be used.
        """
        def update_schema_data(map1: MutableMapping, map2: Mapping):
            if isinstance(map1, Mapping) and isinstance(map2, Mapping):
                for key in map2:
                    if key in map1:
                        if isinstance(map1[key], Mapping) and isinstance(map2[key], Mapping):
                            try:
                                update_schema_data(map1[key], map2[key])
                            except UndefinedScalarMerging as undefined_error:
                                keys = [key]
                                keys.extend(undefined_error.keys)
                                raise UndefinedScalarMerging(keys)
                            except MappingNonMappingMerging as mapping_error:
                                keys = [key]
                                keys.extend(mapping_error.keys)
                                raise MappingNonMappingMerging(keys)
                            except UndefinedSequenceMerging as mapping_error:
                                keys = [key]
                                keys.extend(mapping_error.keys)
                                raise UndefinedSequenceMerging(keys)

                        elif isinstance(map1[key], MutableSequence) and isinstance(map2[key], MutableSequence):
                            if shadow_behavior is None:
                                raise UndefinedSequenceMerging([key])
                            else:
                                map1[key] = shadow_behavior.merge_sequences(map1[key], map2[key], [key])

                        elif not isinstance(map1[key], Mapping) and not isinstance(map2[key], Mapping):
                            if shadow_behavior is None:
                                raise UndefinedScalarMerging([key])
                            else:
                                map1[key] = shadow_behavior.merge_scalars(map1[key], map2[key], key)

                        else:
                            raise MappingNonMappingMerging([key])
                    else:
                        map1[key] = deepcopy(map2[key])
            else:
                raise TypeError("Both map1 and map2 should be Mappable. Received " +
                                "types: {} and {}".format(type(map1), type(map2)))

        if shadow_behavior is None:
            shadow_behavior = ShadowBehavior()

        data_schemas = []
        names = []
        for schema in schemas:
            if not isinstance(schema, Schema):
                raise TypeError("schemas must be a list of Schema objects.")

            data_schema = schema.load(normalize=True)
            if "name" in data_schema:
                names.append(data_schema["name"])
                del data_schema["name"]
            data_schemas.append(data_schema)

        if name is None:
            name = "merged_" + "_".join(names)

        return_schema_data = {"name": name}
        for data_schema in data_schemas:
            try:
                update_schema_data(return_schema_data, data_schema)
            except (UndefinedScalarMerging, UndefinedSequenceMerging) as e:
                value1 = get_node(return_schema_data, e.keys)
                value2 = get_node(data_schema, e.keys)
                raise ValueError("Trying to merge the values {} and {} at ".format(value1, value2) +
                                 "node {}, but no shadow_behavior has been passed ".format(e.keys) +
                                 "as arguments to specify which values should be " +
                                 "overshadowed by the other.")
            except MappingNonMappingMerging as e:
                value1 = get_node(return_schema_data, e.keys)
                value2 = get_node(data_schema, e.keys)
                raise ValueError("Trying to merge the values {} and {} at ".format(value1, value2) +
                                 "node {}, but mappings and scalar cannot be ".format(e.keys) +
                                 "merged with one another.")

        return Schema(return_schema_data)

    @property
    def schema_io(self):
        if self._path != string_io_path:
            self.make_file_object()
        return self._schema_io

    def make_file_object(self):
        if self._path == string_io_path:
            return

        self._schema_io = io.StringIO(self._path.read_text())
        self._path = string_io_path

    def save(self, path):
        if self._path != string_io_path:
            warn("The schema is already a save file {} on the disk. Doing nothing.".format(self._path))
            return

        self._path = Path(path)
        self._path.write_text(self._schema_io.read())
        self._schema_io = None

    def normalize(self):
        yaml_str = yaml.dump(self.load(normalize=True), indent=4, sort_keys=True, Dumper=Dumper)
        self._insertion_node = ()
        self._path = string_io_path
        self._schema_io = io.StringIO(yaml_str)

    def load(self, normalize=True):
        if self._path == string_io_path and self._schema_io is not None:
            schema_data = yaml.load(self._schema_io.read(), Loader=ConfigMngLoader)
            self._schema_io.seek(0)
        elif self._path != string_io_path and self._schema_io is None:
            schema_data = yaml.load(self._path.read_text(), Loader=ConfigMngLoader)
        else:
            raise RuntimeError("This Schema object is in an unexpected state.\n" +
                               "self._path: {}\n".format(self._path) +
                               "self._schema_io: {}".format(self._schema_io))

        if not normalize or len(self._insertion_node) == 0:
            return schema_data

        normalized_schema_data = {}
        if "name" in schema_data:
            normalized_schema_data["name"] = schema_data["name"]
            del schema_data["name"]

        last_mapping = None
        node = None
        current_node = normalized_schema_data
        for node in self._insertion_node:
            current_node["type"] = "map"
            current_node["mapping"] = node
            current_node["mapping"] = {}
            current_node["mapping"][node] = {}
            last_mapping = current_node["mapping"]
            current_node = current_node["mapping"][node]

        last_mapping[node] = schema_data

        return normalized_schema_data


ScalarSchemaArg = typing.TypeVar('ScalarSchemaArg', MutableMapping, io.StringIO, str, Path, Schema)
SchemaArg = typing.Union[ScalarSchemaArg, typing.Sequence[ScalarSchemaArg]]
