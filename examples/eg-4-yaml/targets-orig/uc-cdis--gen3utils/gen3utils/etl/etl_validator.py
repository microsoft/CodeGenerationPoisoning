from collections import defaultdict
from packaging import version
import yaml
import re

from gen3utils.manifest.manifest_validator import get_manifest_version
from gen3utils.etl.dd_utils import init_dictionary
from gen3utils.errors import MappingError, PropertiesError, PathError, FieldError


class Prop:
    def __init__(self, name):
        self.name = name


class Index:
    def __init__(self, name, underscore=False):
        self.name = name
        if underscore:
            id_name = "_{}_id".format(name)
        else:
            id_name = "{}_id".format(name)
        self.props = {id_name: Prop(id_name)}


def validate_joining_list_props(props_list, recorded_errors, existing_indices):
    if type(props_list) is list:
        for prop in props_list:
            if "index" in prop and "join_on" in prop:
                for real_prop in prop.get("props"):
                    validate_joining_prop(
                        real_prop,
                        recorded_errors,
                        existing_indices.get(prop.get("index")),
                    )


def validate_list_props(
    props_list,
    labels_to_back_refs,
    nodes_with_props,
    recorded_errors,
    grouping_path,
    index,
    nodes_for_category=None,
):
    if not nodes_for_category:
        nodes_for_category = []

    if type(props_list) is list:
        for prop in props_list:
            if "path" in prop and "props" in prop:  # flatten_props
                for real_prop in prop.get("props"):
                    new_props = validate_prop(
                        real_prop,
                        labels_to_back_refs,
                        nodes_with_props,
                        recorded_errors,
                        prop.get("path", grouping_path),
                    )
                    index.props.update({p.name: p for p in new_props})
            elif "index" in prop and "join_on" in prop:  # joining_props
                # joining_props does not require path (considering it later after having all indices)
                return
            else:
                new_props = validate_prop(
                    prop,
                    labels_to_back_refs,
                    nodes_with_props,
                    recorded_errors,
                    grouping_path,
                    nodes_for_category,
                )
                index.props.update({p.name: p for p in new_props})
            # joining_props which contain join_on and index will be validated after all indices are walked through
    elif type(props_list) is dict:
        for k, v in props_list.items():
            if k in labels_to_back_refs.keys():
                for prop in v.get("props"):
                    new_props = validate_prop(
                        prop,
                        labels_to_back_refs,
                        nodes_with_props,
                        recorded_errors,
                        labels_to_back_refs.get(k),
                    )
                    index.props.update({p.name: p for p in new_props})


def validate_joining_prop(json_obj, recorded_errors, joining_index):
    name = validate_name(json_obj, recorded_errors)
    validate_fn(json_obj, recorded_errors)
    validate_joining_src(json_obj, recorded_errors, joining_index.props)
    return Prop(name)


def validate_prop(
    json_obj,
    labels_to_back_refs,
    nodes_with_props,
    recorded_errors,
    grouping_path=None,
    nodes_for_category=None,
):
    if not nodes_for_category:
        nodes_for_category = []

    names = validate_path(
        json_obj,
        grouping_path,
        recorded_errors,
        labels_to_back_refs,
        nodes_with_props,
        nodes_for_category,
    )
    if len(names) == 0:
        names.append(
            validate_name_src(
                json_obj,
                json_obj.get("path", grouping_path),
                recorded_errors,
                nodes_with_props,
                labels_to_back_refs,
                nodes_for_category,
            )
        )

    props = [Prop(n) for n in names]
    return props


def validate_joining_src(json_obj, recorded_errors, joining_props):
    src = json_obj.get("src", json_obj.get("name"))
    alternate_src = json_obj.get("alternate_src", json_obj.get("name"))
    if src is not None:
        if src not in joining_props:
            if alternate_src in joining_props:
                print("WARN: Utilizing alternate src")
                return
            recorded_errors.append(
                FieldError(
                    'src field "{}" (declared in "{}") is not found in joining index.'.format(
                        src, json_obj
                    )
                )
            )
    else:
        recorded_errors.append(
            FieldError('Missing source field for "{}"'.format(json_obj))
        )


def validate_fn(json_obj, recorded_errors):
    fn = json_obj.get("fn")
    if fn is not None:
        if fn not in ["set", "count", "list", "sum", "min", "max"]:
            recorded_errors.append(
                MappingError(
                    '"{}" function (declared in "{}") is not supported in ETL'.format(
                        fn, json_obj
                    ),
                    "Function",
                )
            )
    return fn


def validate_name(json_obj, recorded_errors):
    name = json_obj.get("name")
    if name is None or name == "":
        recorded_errors.append(
            PropertiesError(
                'Name is missing or empty string for mapping property "{}".'.format(
                    json_obj
                )
            )
        )
    return name


def validate_name_src(
    json_obj,
    path,
    recorded_errors,
    nodes_with_props,
    labels_to_back_refs=None,
    nodes_for_category=None,
):
    if not labels_to_back_refs:
        labels_to_back_refs = {}
    if not nodes_for_category:
        nodes_for_category = []

    name = validate_name(json_obj, recorded_errors)
    fn = validate_fn(json_obj, recorded_errors)
    src = json_obj.get("src", name)
    if not src:
        return name
    if not path and not nodes_for_category:
        recorded_errors.append(
            FieldError(
                'src field must be specified with a path for "{}"'.format(json_obj)
            )
        )
    else:
        valid_fields = {"source_node"}  # built-in fields
        if path:
            path_items = path.split(".")
            valid_fields.update(nodes_with_props.get(path_items[-1], []))
        for node_name in nodes_for_category:
            node_backref = labels_to_back_refs[node_name]
            node_props = nodes_with_props.get(node_backref, [])
            valid_fields.update(node_props)
        if fn != "count" and src not in valid_fields:
            recorded_errors.append(
                FieldError(
                    'src field "{}" (declared in {} "{}") is not found in given dictionary.'.format(
                        src, f'"{path}"' if path else "a collector index", json_obj
                    )
                )
            )
    return name


def validate_path(
    json_obj,
    grouping_path,
    recorded_errors,
    labels_to_back_refs,
    nodes_with_props,
    nodes_for_category=None,
):
    if not nodes_for_category:
        nodes_for_category = []
    nodes_for_category_backrefs = [labels_to_back_refs[n] for n in nodes_for_category]

    path = json_obj.get("path", grouping_path)
    names = []
    if path:
        nodes_for_category_backrefs.append(path)
    if not nodes_for_category_backrefs:
        recorded_errors.append(
            PropertiesError(
                'Missing path declaration for the property "{}".'.format(json_obj)
            )
        )
    else:
        for path in nodes_for_category_backrefs:
            # handle format "node1[id].node2[id]":
            path_items = path.split(".")
            if "_ANY" in path_items:
                path_items.remove("_ANY")
            for item in path_items:
                # get the edge name and the property definition from line:
                # subjects[subject_id:id,project_id]
                [edge, str_fields] = (
                    list(filter(None, re.split(r"[\[\]]", item)))
                    if "[" in item
                    else [item, None]
                )
                if edge not in labels_to_back_refs.values():
                    recorded_errors.append(PathError(path))
                if str_fields is not None:
                    fields = str_fields.split(",")
                    for f in fields:
                        name, src = (
                            [p.strip() for p in f.split(":")]
                            if ":" in f
                            else [f.strip()] * 2
                        )
                        names.append(
                            validate_name_src(
                                {"name": name, "src": src},
                                edge,
                                recorded_errors,
                                nodes_with_props,
                            )
                        )
    return names


def get_all_nodes(model):
    labels_to_back_refs = {}
    """
    dictionary from label to back_ref
    {
        "subject": "subjects"
    }
    """
    nodes_with_props = {}
    """
    dictionary nodes (with plural) to all properties
    {
        "subjects": [
            "submitter_id",
            "project_id",
            "species"
        ]
    }
    """
    categories_to_labels = defaultdict(list)
    """
    group label by its category
    {
        "data_file": [
            submitted_aligned_reads,
            submitted_unaligned_reads
        ]
    }
    """
    all_classes = model.Node.get_subclasses()
    for n in all_classes:
        present_links = n._pg_edges
        present_props = n.__pg_properties__
        present_node_props = list(present_props.keys()) + ["id"]
        category = n._dictionary.get("category")
        categories_to_labels[category].append(n.label)
        backref = ""
        if len(present_links) > 0:
            backref = list(present_links.values())[0].get("backref")
            labels_to_back_refs[n.label] = backref
        nodes_with_props.update({backref: present_node_props})
    return labels_to_back_refs, nodes_with_props, categories_to_labels


def check_mapping_format(mappings, recorded_errors):
    # TODO add more checks to this
    if "mappings" not in mappings:
        recorded_errors.append(
            MappingError('etlMapping file does not contain "mappings"', "format")
        )
        return recorded_errors
    for m in mappings.get("mappings"):
        if "doc_type" not in m:
            recorded_errors.append(
                MappingError(
                    'Mapping "{}" does not contain "doc_type"'.format(m.get("name")),
                    "format",
                )
            )
    return recorded_errors


def check_mapping_constraints(mappings, model, recorded_errors, underscore):
    labels_to_back_refs, nodes_with_props, categories_to_labels = get_all_nodes(model)
    indices = {}
    for m in mappings.get("mappings"):
        index = Index(m.get("doc_type"), underscore)
        indices[index.name] = index
        category = m.get("category")
        node_name = m.get("root")
        for key, value in m.items():
            if key.endswith("props"):
                if key not in [
                    "props",
                    "flatten_props",
                    "parent_props",
                    "nested_props",
                    "joining_props",
                    "aggregated_props",
                    "injecting_props",
                ]:
                    recorded_errors.append(
                        MappingError(
                            f"{key} is not a valid property type", "PropertyType"
                        )
                    )
                root_path = (
                    labels_to_back_refs.get(node_name) if key == "props" else None
                )
                nodes_for_category = categories_to_labels.get(category, [])
                validate_list_props(
                    value,
                    labels_to_back_refs,
                    nodes_with_props,
                    recorded_errors,
                    root_path,
                    index,
                    nodes_for_category,
                )
        if (
            m.get("type") == "aggregator"
            and m.get("root") != "project"
            and "project_id" not in index.props
        ):
            recorded_errors.append(
                PropertiesError(f"project_id is not found in index {index.name}")
            )

    for m in mappings.get("mappings"):
        joining_props = m.get("joining_props", [])
        validate_joining_list_props(joining_props, recorded_errors, indices)
    return recorded_errors


def is_release_tag(parsed_version):
    """
    Args:
        parsed_version: releases.version
    Returns:
        bool: True if version's major number is >= 2019. This is true of
        our current monthly release versions (e.g. 2020.05, 2019.11) but not
        true of our standard semver versions (e.g. 2.33.0)
    """
    return parsed_version >= version.parse("2019.0")


def validate_mapping(dictionary_url, mapping_file, manifest):
    dictionary, model = init_dictionary(dictionary_url)
    with open(mapping_file) as f:
        mappings = yaml.safe_load(f)

    # If using tube >= 0.4.0 or >= 2020.10, {doc_type}_id fields have a prefixed underscore.
    # https://github.com/uc-cdis/tube/releases/tag/0.4.0
    tube_version = get_manifest_version(
        manifest["versions"], "tube", release_tag_are_branches=False, warn=False
    )
    underscore = False
    if tube_version is not None and type(tube_version) != str:  # str if branch
        if not is_release_tag(tube_version) and tube_version >= version.parse("0.4.0"):
            underscore = True
        elif tube_version >= version.parse("2020.10"):
            underscore = True

    recorded_errors = check_mapping_format(mappings, [])
    if len(recorded_errors) > 0:
        return recorded_errors

    return check_mapping_constraints(mappings, model, recorded_errors, underscore)
