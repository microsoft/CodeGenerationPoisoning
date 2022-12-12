import re
import yaml
import json
import os

from cdislogging import get_logger

from gen3utils.assertion import assert_and_log
from gen3utils.etl.dd_utils import init_dictionary
from gen3utils.errors import FieldSyntaxError, FieldError
from gen3utils.deployment_changes.generate_comment import submit_comment


logger = get_logger("validate-portal-config", log_level="info")


def val_gitops(data_dictionary, etl_mapping, gitops):
    with open(gitops, "r") as f:
        gitops_config = json.loads(f.read())
    ok = validate_gitops_syntax(gitops_config)
    if not ok:
        raise AssertionError(
            "Portal configuration failed. See errors in previous logs."
        )

    ok = validate_against_dictionary(gitops_config, data_dictionary)
    recorded_errors = validate_against_etl(gitops_config, etl_mapping)
    return recorded_errors, ok


def validate_gitops_syntax(gitops):
    """
    Validates the syntax of gitops.json by checking for required fields
    Args:
        gitops (dict): gitops.json config

    Returns:
        Error: Returns the error if it exists, else returns None.

    TODO
    Currently only checks syntax needed for etl mapping and dictionary validation.
    """
    graphql = gitops.get("graphql")
    ok = assert_and_log(graphql, FieldSyntaxError("graphql"))

    if graphql:
        ok = ok and assert_and_log(
            "boardCounts" in graphql, FieldSyntaxError("graphql.boardCounts")
        )
        boardcounts = graphql.get("boardCounts", [])
        if boardcounts:
            for item in boardcounts:
                checks = ["graphql", "name", "plural"]
                ok = check_required_fields("graphql.boardCounts", checks, item, ok)

        ok = ok and assert_and_log(
            "chartCounts" in graphql, FieldSyntaxError("graphql.chartCounts")
        )

    components = gitops.get("components")
    ok = ok and assert_and_log(components, FieldSyntaxError("components"))
    if components:
        index = components.get("index")
        ok = ok and assert_and_log(index, FieldSyntaxError("components.index"))
        if index:
            homepage = index.get("homepageChartNodes", [])
            ok = ok and assert_and_log(
                index, FieldSyntaxError("components.homepageChartNodes")
            )
            for item in homepage:
                checks = ["node", "name"]
                ok = check_required_fields(
                    "components.index.homepage", checks, item, ok
                )

        # footerLogos is optional, but when present, it must be an array (list)
        footerLogos = components.get("footerLogos", [])
        ok = ok and assert_and_log(
            isinstance(footerLogos, list),
            FieldError("footerLogos must be an array if presents in the config"),
        )

    explorer_enabled = gitops.get("featureFlags", {}).get("explorer", True)
    explorerconfig = gitops.get("explorerConfig")
    configs = []
    if not explorerconfig:
        dataConfig = gitops.get("dataExplorerConfig")
        fileConfig = gitops.get("fileExplorerConfig")
        ok = ok and assert_and_log(
            dataConfig or not explorer_enabled, FieldSyntaxError("(data)explorerConfig")
        )
        if dataConfig:
            configs.append(dataConfig)
        if fileConfig:
            configs.append(fileConfig)
    else:
        configs = explorerconfig

    for exp_config in configs:
        filters = exp_config.get("filters")
        ok = ok and assert_and_log(filters, FieldSyntaxError("explorerConfig.filters"))
        if filters:
            tabs = filters.get("tabs", [])
            ok = ok and assert_and_log(
                tabs, FieldSyntaxError("explorerConfig.filters.tabs")
            )
            for tab in tabs:
                checks = ["title", "fields"]
                ok = check_required_fields(
                    "explorerConfig.filters.tab", checks, tab, ok
                )

        guppy = exp_config.get("guppyConfig")
        ok = ok and assert_and_log(
            guppy, FieldSyntaxError("explorerConfig.guppyConfig")
        )
        buttons = exp_config.get("buttons", [])
        manifest_mapping = None
        if guppy:
            ok = ok and assert_and_log(
                guppy.get("dataType"),
                FieldSyntaxError("explorerConfig.guppyConfig.dataType"),
            )
            manifest_mapping = guppy.get("manifestMapping")

        val_mapping = False
        for button in buttons:
            if button.get("enabled") and button.get("type") == "manifest":
                val_mapping = True
        if manifest_mapping and val_mapping:
            checks = [
                "resourceIndexType",
                "resourceIdField",
                "referenceIdFieldInResourceIndex",
                "referenceIdFieldInDataIndex",
            ]
            ok = check_required_fields(
                "explorerConfig.guppyConfig.manifestMapping",
                checks,
                manifest_mapping,
                ok,
            )

    study_viewer = gitops.get("studyViewerConfig")

    if study_viewer:
        checks = [
            "dataType",
            "listItemConfig",
            "rowAccessor",
        ]
        for viewer in study_viewer:
            ok = check_required_fields("studyViewerConfig", checks, viewer, ok)

    return ok


def check_required_fields(path, checks, field, ok):
    for check in checks:
        ok = ok and assert_and_log(
            field.get(check), FieldSyntaxError(f"{path}.{check}")
        )
    return ok


def check_field_value(path, checks, accepted_values, errors):
    for check in checks:
        if check not in accepted_values:
            errors.append(
                FieldError(
                    "Field [{}] in {} not found in etlMapping".format(check, path)
                )
            )


def _validate_itemConfig(item_config, props, typ, errors):
    check_field_value(
        "studyViewerConfig.blockFields.{}ItemConfig".format(typ),
        item_config.get("blockFields", []),
        props,
        errors,
    )
    check_field_value(
        "studyViewerConfig.tableFields.{}ItemConfig".format(typ),
        item_config.get("tableFields", []),
        props,
        errors,
    )


def _validate_studyViewer_datatypes(
    viewer, datatype, type_prop_map, row_accessor, errors
):
    dtype = viewer.get(datatype)
    props = type_prop_map.get(dtype, [])
    if not props:
        errors.append(
            FieldError(
                "Field [{}] in studyViewerConfig.{} not found in etlMapping".format(
                    dtype, datatype
                )
            )
        )
    if row_accessor not in props:
        errors.append(
            FieldError(
                "rowAccessor [{}] not found in index with type {}".format(
                    row_accessor, dtype
                )
            )
        )


def _validate_studyViewerConfig_helper(viewer, type_prop_map, errors):
    dtype = viewer.get("dataType")
    checks = ["dataType"]
    for optional in ["fileDataType", "docDataType"]:
        if viewer.get(optional):
            checks.append(optional)

    for datatype in checks:
        _validate_studyViewer_datatypes(
            viewer, datatype, type_prop_map, viewer["rowAccessor"], errors
        )
    props = type_prop_map.get(dtype, [])
    listitemconfig = viewer.get("listItemConfig")
    _validate_itemConfig(listitemconfig, props, "list", errors)
    if viewer.get("singleItemConfig"):
        _validate_itemConfig(viewer.get("singleItemConfig"), props, "single", errors)


def validate_studyViewerConfig(studyviewer, type_prop_map, errors):
    for viewer in studyviewer:
        _validate_studyViewerConfig_helper(viewer, type_prop_map, errors)


def _validate_explorerConfig_helper(explorer_config, type_prop_map, errors):

    datatype = explorer_config["guppyConfig"]["dataType"]
    props = type_prop_map.get(datatype, [])
    if not props:
        errors.append(
            FieldError(
                "Field [{}] in explorerConfig.guppyConfig.dataType not found in etlMapping".format(
                    datatype
                )
            )
        )

    tabs = explorer_config["filters"]["tabs"]
    for tab in tabs:
        check_field_value(
            "explorerConfig.filters.tabs.fields", tab.get("fields", []), props, errors
        )

    table = explorer_config["table"]
    if table["enabled"]:
        check_field_value(
            "explorerConfig.table.fields", table.get("fields", []), props, errors
        )

    manifest_map = explorer_config.get("manifestMapping")
    if manifest_map and manifest_map.get("resourceIndexType"):
        resource_props = type_prop_map.get(manifest_map.get("resourceIndexType"))
        if not resource_props:
            errors.append(
                FieldError(
                    "Field [{}] in manifestMapping.resourceIndexType not found in etlMapping".format(
                        manifest_map.get("resourceIndexType")
                    )
                )
            )
        elif manifest_map.get("resourceIdField") not in resource_props:
            errors.append(
                FieldError(
                    "Field [{}] in manifestMapping.resourceIdField not found in etlMapping".format(
                        manifest_map.get("resourceIdField")
                    )
                )
            )
        # TODO
        # Also consider fields referenceIdFieldInResourceIndex and referenceIdFieldInDataIndex


def validate_explorerConfig(gitops, type_prop_map, errors):
    explorer_configs = gitops.get("explorerConfig", [])
    # if explorerConfig exists, ignores (data/files)explorerConfig
    if not explorer_configs:
        if "dataExplorerConfig" in gitops:
            explorer_configs.append(gitops["dataExplorerConfig"])
        if "fileExplorerConfig" in gitops:
            explorer_configs.append(gitops["fileExplorerConfig"])
    for config in explorer_configs:
        _validate_explorerConfig_helper(config, type_prop_map, errors)
    return errors


def validate_against_etl(gitops, mapping_file):
    """
    Validates gitops.json configuration against an etlMapping
    Args:
        gitops (dict): gitops.json config
        mapping_file (str): path to etlMapping file

    Returns:
        Error: Returns a list of any errors encountered.

    """
    with open(mapping_file) as f:
        mappings = yaml.safe_load(f)
    mapping = mappings.get("mappings")
    type_prop_map = map_all_ES_index_props(mapping)
    errors = validate_explorerConfig(gitops, type_prop_map, [])
    studyviewer = gitops.get("studyViewerConfig")
    if studyviewer:
        validate_studyViewerConfig(studyviewer, type_prop_map, errors)

    return errors


def map_all_ES_index_props(mapping):
    """
    Args:
        mapping (dict): The etlMapping to parse

    returns:
        A mapping between each index type and all it's properties
    """
    all_prop_map = {}
    for index in mapping:
        index_props = []
        props = index.get("props")
        index_props.extend(_extract_props(props))
        agg_props = index.get("aggregated_props")
        index_props.extend(_extract_props(agg_props))
        join_props = index.get("joining_props", [])
        for indx in join_props:
            index_props.extend(_extract_props(indx.get("props")))
        inject_props = index.get("injecting_props", {})
        for node, props in inject_props.items():
            index_props.extend(_extract_props(props.get("props")))
        flat_props = index.get("flatten_props", [])
        for node in flat_props:
            index_props.extend(_extract_props(node.get("props")))
        parent_props = index.get("parent_props")
        if parent_props:
            for prop in parent_props:
                # handle format "node1[id].node2[id]":
                path_items = prop.get("path").split(".")
                if "_ANY" in path_items:
                    path_items.remove("_ANY")
                # get the edge name and the property definition from line:
                # subjects[subject_id:id,project_id]
                for item in path_items:
                    [_, str_props] = (
                        list(filter(None, re.split(r"[\[\]]", item)))
                        if "[" in item
                        else [item, None]
                    )
                    if str_props is not None:
                        props = str_props.split(",")
                        index_props.extend(
                            [
                                p.split(":")[0].strip()
                                if p.find(":") != -1
                                else p.strip()
                                for p in props
                            ]
                        )

        all_prop_map[index.get("doc_type")] = set(index_props)

    return all_prop_map


def _extract_props(props_to_extract):
    if not props_to_extract:
        return []
    return [p["name"] for p in props_to_extract]


def validate_against_dictionary(gitops, data_dictionary):
    """
    Validates gitops.json configuration against a data dictionary
    Args:
        gitops (dict): gitops.json config
        data_dictionary (str): url of data dictionary

    Returns:
        ok(bool): whether the validation succeeded.

    """

    _, model = init_dictionary(data_dictionary)
    schema = model.dictionary.schema

    ok = True
    graphql = gitops["graphql"]
    for item in graphql["boardCounts"]:
        node_count = item["graphql"]
        # assumes form _{node}_count
        idx = node_count.rfind("_")
        node = node_count[1:idx]

        ok = ok and assert_and_log(
            schema.get(node) is not None,
            "Node: {} in graphql.boardCounts not found in dictionary".format(node),
        )

    for item in graphql["chartCounts"]:
        node_count = item["graphql"]
        # assumes form _{node}_count
        idx = node_count.rfind("_")
        node = node_count[1:idx]
        ok = ok and assert_and_log(
            schema.get(node) is not None,
            "Node: {} in graphql.chartCounts not found in dictionary".format(node),
        )

    for item in graphql.get("homepageChartNodes", []):
        node = item["node"]
        ok = ok and assert_and_log(
            schema.get(node) is not None,
            "Node: {} in graphql.homepageChartNodes not found in dictionary".format(
                node
            ),
        )

    return ok
