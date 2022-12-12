# pxylint: disable=attribute-defined-outside-init
import itertools
import logging
import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List

import cwrap
import numpy as np
import yaml
from ecl.ecl_type import EclDataType
from ecl.eclfile import Ecl3DKW
from ecl.grid.ecl_grid import EclGrid
from ecl.util.geometry import Surface
from numpy import ma
from ert._c_wrappers.enkf.enums.enkf_var_type_enum import EnkfVarType
from ert._c_wrappers.enkf.enums.ert_impl_type_enum import ErtImplType
from ert._c_wrappers.enkf.row_scaling import RowScaling

from semeio.workflows.localisation.localisation_debug_settings import (
    LogLevel,
    debug_print,
)


@dataclass
class Parameter:
    name: str
    type: str
    parameters: List = field(default_factory=list)

    def to_list(self):
        if self.parameters:
            return [f"{self.name}:{parameter}" for parameter in self.parameters]
        return [f"{self.name}"]

    def to_dict(self):
        return {self.name: self.parameters}


@dataclass
class Parameters:
    parameters: List[Parameter] = field(default_factory=list)

    def append(self, new):
        # pylint: disable=no-member
        # (false positive)
        self.parameters.append(new)

    def to_list(self):
        # pylint: disable=not-an-iterable
        # (false positive)
        result = []
        for parameter in self.parameters:
            result.extend(parameter.to_list())
        return result

    def to_dict(self):
        # pylint: disable=not-an-iterable
        # (false positive)
        result = {}
        for parameter in self.parameters:
            if parameter.name in result:
                raise ValueError(f"Duplicate parameters found: {parameter.name}")
            result.update(parameter.to_dict())
        return result

    @classmethod
    def from_list(cls, input_list):
        result = defaultdict(list)
        for item in input_list:
            words = item.split(":")
            if len(words) == 1:
                name = words[0]
                parameters = None
            elif len(words) == 2:
                name, parameters = words
            else:
                raise ValueError(f"Too many : in {item}")
            if name in result:
                if not parameters:
                    raise ValueError(
                        f"Inconsistent parameters, found {name} in "
                        f"{dict(result)}, but did not find parameters"
                    )
                if not result[name]:
                    raise ValueError(
                        f"Inconsistent parameters, found {name} in {dict(result)} but "
                        f"did not expect parameters, found {parameters}"
                    )
            if parameters:
                result[name].append(parameters)
            else:
                result[name] = []
        return cls([Parameter(key, "UNKNOWN", val) for key, val in result.items()])


def get_param_from_ert(ens_config):
    new_params = Parameters()
    keylist = ens_config.alloc_keylist()
    implementation_type_not_scalar = [
        ErtImplType.GEN_DATA,
        ErtImplType.FIELD,
        ErtImplType.SURFACE,
    ]
    for key in keylist:
        node = ens_config.getNode(key)
        impl_type = node.getImplementationType()
        if node.getVariableType() == EnkfVarType.PARAMETER:
            my_param = Parameter(key, impl_type)
            new_params.append(my_param)
            if impl_type == ErtImplType.GEN_KW:
                # Node contains scalar parameters defined by GEN_KW
                kw_config_model = node.getKeywordModelConfig()
                my_param.parameters = kw_config_model.getKeyWords().strings
            elif impl_type in implementation_type_not_scalar:
                # Node contains parameter from FIELD, SURFACE or GEN_PARAM
                # The parameters_for_node dict contains empty list for FIELD
                # and SURFACE.
                # The number of variables for a FIELD parameter is
                # defined by the grid in the GRID keyword.
                # The number of variables for a SURFACE parameter is
                # defined by the size of a surface object.
                # For GEN_PARAM the list contains the number of variables.
                # parameters_for_node[key] = []
                if impl_type == ErtImplType.GEN_DATA:
                    gen_data_config = node.getDataModelConfig()
                    data_size = gen_data_config.get_initial_size()
                    if data_size <= 0:
                        # Cannot here know if it will be used or not.
                        logging.warning(
                            "\nThe ERT config has defined parameter nodes of type\n"
                            "GEN_PARAM. If this is used in localisation, \n"
                            "the localisation workflow must be run AFTER initial \n"
                            "ensemble is created, but BEFORE first update is run.\n\n"
                        )

                    my_param.parameters = [str(item) for item in range(data_size)]

    return new_params


def read_localisation_config(args):
    if len(args) == 1:
        specification_file_name = args[0]
    else:
        raise ValueError(f"Expecting a single argument. Got {args} arguments.")

    print(f"\nDefine localisation setup using config file: {specification_file_name}")
    logging.info(
        "\nDefine localisation setup using config file: %s", specification_file_name
    )
    with open(specification_file_name, "r", encoding="utf-8") as yml_file:
        localisation_yml = yaml.safe_load(yml_file)
    return localisation_yml


def active_index_for_parameter(node_name, param_name, ert_param_dict):
    # For parameters defined as scalar parameters (coming from GEN_KW)
    # the parameters for a node have a name. Get the index from the order
    # of these parameters.

    ert_param_list = ert_param_dict[node_name]
    if len(ert_param_list) > 0:
        index = -1
        for count, name in enumerate(ert_param_list):
            if name == param_name:
                index = count
                break
        assert index > -1
    return index


def activate_gen_kw_param(
    node_name, param_list, ert_param_dict, log_level=LogLevel.OFF
):
    """
    Activate the selected parameters for the specified node.
    The param_list contains the list of parameters defined in GEN_KW
    for this node to be activated.
    """
    debug_print("Set active parameters", LogLevel.LEVEL2, log_level)
    index_list = []
    for param_name in param_list:
        index = active_index_for_parameter(node_name, param_name, ert_param_dict)
        if index is not None:
            debug_print(
                f"Active parameter: {param_name}  index: {index}",
                LogLevel.LEVEL3,
                log_level,
            )
            index_list.append(index)
    return index_list


def activate_gen_param(node_name, param_list, data_size, log_level=LogLevel.OFF):
    """
    Activate the selected parameters for the specified node.
    The param_list contains a list of names that are integer numbers
    for the parameter indices to be activated for parameters belonging
    to the specified GEN_PARAM node.
    """
    index_list = []
    for param_name in param_list:
        index = int(param_name)
        if index < 0 or index >= data_size:
            raise ValueError(
                f"Index for parameter in node {node_name} is "
                f"outside the interval [0,{data_size-1}]"
            )
        debug_print(f"Active parameter index: {index}", LogLevel.LEVEL3, log_level)
        index_list.append(index)
    return index_list


def apply_decay(
    method,
    row_scaling,
    data_size,
    grid,
    ref_pos,
    main_range,
    perp_range,
    azimuth,
    use_cutoff=False,
    tapering_range=None,
    calculate_qc_parameter=False,
):
    # pylint: disable=too-many-arguments,too-many-locals
    """Calculates the scaling factor, assign it to ERT instance by row_scaling
    and returns a full sized grid parameter with scaling factors for active
    grid cells and 0 elsewhere to be used for QC purpose.
    """
    if method == "gaussian_decay":
        decay_obj = GaussianDecay(
            ref_pos,
            main_range,
            perp_range,
            azimuth,
            grid,
            use_cutoff,
        )
    elif method == "exponential_decay":
        decay_obj = ExponentialDecay(
            ref_pos,
            main_range,
            perp_range,
            azimuth,
            grid,
            use_cutoff,
        )
    elif method == "const_gaussian_decay":
        decay_obj = ConstGaussianDecay(
            ref_pos,
            main_range,
            perp_range,
            azimuth,
            grid,
            tapering_range,
            use_cutoff,
        )
    elif method == "const_exponential_decay":
        decay_obj = ConstExponentialDecay(
            ref_pos,
            main_range,
            perp_range,
            azimuth,
            grid,
            tapering_range,
            use_cutoff,
        )
    else:
        _valid_methods = [
            "gaussian_decay",
            "exponential_decay",
            "const_gaussian_decay",
            "const_exponential_decay",
        ]
        raise NotImplementedError(
            f"The only allowed methods for function 'apply_decay' are: {_valid_methods}"
        )

    scaling_vector = np.zeros(data_size, dtype=np.float32)
    for index in range(data_size):
        scaling_vector[index] = decay_obj(index)
    row_scaling.assign_vector(scaling_vector)

    scaling_values = None
    if calculate_qc_parameter:
        if isinstance(grid, EclGrid):
            nx = grid.getNX()
            ny = grid.getNY()
            nz = grid.getNZ()
            scaling_values = np.zeros(nx * ny * nz, dtype=np.float32)
            for index in range(data_size):
                global_index = grid.global_index(active_index=index)
                scaling_values[global_index] = scaling_vector[index]

    return scaling_values


def apply_from_file(row_scaling, data_size, grid, filename, param_name, log_level):
    # pylint: disable=too-many-arguments
    debug_print(
        f"Read scaling factors as parameter {param_name}", LogLevel.LEVEL3, log_level
    )
    debug_print(f"File name:  {filename}", LogLevel.LEVEL3, log_level)
    with cwrap.open(filename, "r") as file:
        scaling_parameter = Ecl3DKW.read_grdecl(
            grid,
            file,
            param_name,
            strict=True,
            ecl_type=EclDataType.ECL_FLOAT,
        )
        for index in range(data_size):
            global_index = grid.global_index(active_index=index)
            row_scaling[index] = scaling_parameter[global_index]


def active_region(region_parameter, user_defined_active_region_list):
    """
     Find all region parameter values matching any of the regions defined
    to be used in localisation and mask the unused values
    """
    active_region_values_used = ma.zeros(len(region_parameter), dtype=np.int32)
    active_region_values_used[:] = -9999
    for region_number in user_defined_active_region_list:
        found_values = region_parameter == region_number
        active_region_values_used[found_values] = region_number
    is_not_used = active_region_values_used == -9999
    active_region_values_used.mask = is_not_used
    return active_region_values_used


def define_look_up_index(user_defined_active_region_list, max_region_number):
    """
    Define an array taking region number as input and returning the index in the
    user define active region list. Is used for fast lookup of scaling parameter
    corresponding to the region number.
    """
    active_segment_array = np.array(user_defined_active_region_list)
    index_per_used_region = ma.zeros((max_region_number + 1), dtype=np.uint16)
    index_values = np.arange(len(active_segment_array))
    index_per_used_region[active_segment_array[index_values]] = index_values
    return index_per_used_region


def calculate_scaling_factors_in_regions(
    grid, region_parameter, active_segment_list, scaling_value_list, smooth_range_list
):
    # pylint: disable=unused-argument,too-many-locals
    # ('grid' and 'smooth-range-list' are not currently used)

    min_region_number = region_parameter.min()
    max_region_number = region_parameter.max()

    # Get a list of region numbers that exists in region parameter
    regions_in_param = []
    for region_number in range(min_region_number, max_region_number + 1):
        has_region = region_parameter == region_number
        if has_region.any():
            regions_in_param.append(region_number)

    active_region_values_used = active_region(region_parameter, active_segment_list)
    index_per_used_region = define_look_up_index(active_segment_list, max_region_number)
    scaling_value_array = np.array(scaling_value_list)

    # Get selected (not masked) region values
    selected_grid_cells = np.logical_not(active_region_values_used.mask)
    selected_region_values = active_region_values_used[selected_grid_cells]

    # Look up scaling values for selected region values
    scaling_values_active = scaling_value_array[
        index_per_used_region[selected_region_values]
    ]

    # Create a full sized 3D parameter for scaling values
    # where all but the selected region values have 0 scaling value.
    scaling_values = np.zeros(len(region_parameter), dtype=np.float32)
    scaling_values[selected_grid_cells] = scaling_values_active

    return scaling_values, active_region_values_used, regions_in_param


def smooth_parameter(
    grid, smooth_range_list, scaling_values, active_region_values_used
):
    """
    Function taking as input a 3D parameter  scaling_values and calculates a new
    3D parameter scaling_values_smooth using local average within a rectangular window
    around the cell to be assigned the smoothed value. The smoothing window is
    defined by the two range parameters in smooth_range_list.
    They contain integer values >=0 and smooth_range_list = [0,0] means no smoothing.
    The input parameter active_region_values_used has non-negative integer values
    with region number for all grid cells containing values for the input 3D parameter
    scaling_values. All other grid cells are masked.
    The smoothing algorithm is defined such that only values not masked are used.
    If the  scaling_values contain constant values for each
    active region and e.g 0 for all inactive regions and for inactive grid cells,
    then the smoothing will only appear on the border between active regions.
    """
    # pylint: disable=too-many-locals
    nx = grid.get_nx()
    ny = grid.get_ny()
    nz = grid.get_nz()
    di = smooth_range_list[0]
    dj = smooth_range_list[1]
    scaling_values_smooth = np.zeros(nx * ny * nz, dtype=np.float32)
    for k, j0, i0 in itertools.product(range(nz), range(ny), range(nx)):
        index0 = i0 + j0 * nx + k * nx * ny
        if not active_region_values_used[index0] is ma.masked:
            sumv = 0.0
            nval = 0
            ilow = max(0, i0 - di)
            ihigh = min(i0 + di + 1, nx)
            jlow = max(0, j0 - dj)
            jhigh = min(j0 + dj + 1, ny)
            for i in range(ilow, ihigh):
                for j in range(jlow, jhigh):
                    index = i + j * nx + k * nx * ny
                    if not active_region_values_used[index] is ma.masked:
                        # Only use values from grid cells that are active
                        # and from regions defined as active by the user.
                        v = scaling_values[index]
                        sumv += v
                        nval += 1
            if nval > 0:
                scaling_values_smooth[index0] = sumv / nval
    return scaling_values_smooth


def apply_segment(
    row_scaling,
    data_size,
    grid,
    region_param_dict,
    active_segment_list,
    scaling_factor_list,
    smooth_range_list,
    corr_name,
    log_level=LogLevel.OFF,
):
    # pylint: disable=too-many-arguments,too-many-locals
    """
    Purpose: Use region numbers and list of scaling factors per region to
                   create scaling factors per active .
                   Input dictionary with keyword which is correlation group name,
                   where values are numpy vector with region parameters
                   for each grid cell in ERTBOX grid.
                   A scaling factor is specified for each specified active region.
                   Optionally also a spatial smoothing of the scaling factors
                   can be done by specifying smooth ranges in number of
                   grid cells in I and J direction. If this is not specified,
                   no smoothing is done.
                   NOTE: Smoothing is done only between active segments,
                   and no smoothing between active segments and inactive
                   segments or inactive grid cells.
    """

    debug_print(f"Active segments: {active_segment_list}", LogLevel.LEVEL3, log_level)

    max_region_number_specified = max(active_segment_list)

    region_parameter = region_param_dict[corr_name]
    max_region_parameter = region_parameter.max()
    if max_region_parameter < max_region_number_specified:
        raise ValueError(
            "Specified an active region with number "
            f"{max_region_number_specified} which is larger \n"
            f"than max region parameter {max_region_parameter} for "
            f"correlation group {corr_name}."
        )

    (
        scaling_values,
        active_localisation_region,
        regions_in_param,
    ) = calculate_scaling_factors_in_regions(
        grid,
        region_parameter,
        active_segment_list,
        scaling_factor_list,
        smooth_range_list,
    )
    if smooth_range_list is not None:
        scaling_values = smooth_parameter(
            grid, smooth_range_list, scaling_values, active_localisation_region
        )

    # Assign values to row_scaling object
    for index in range(data_size):
        global_index = grid.global_index(active_index=index)
        row_scaling[index] = scaling_values[global_index]

    not_defined_in_region_param = []
    for n in active_segment_list:
        if n not in regions_in_param:
            not_defined_in_region_param.append(n)
    if len(not_defined_in_region_param) > 0:
        debug_print(
            f"Warning: The following region numbers are specified in \n"
            "                config file for correlation group "
            f"{corr_name}, \n"
            "                but not found in region parameter: "
            f"{not_defined_in_region_param}",
            LogLevel.LEVEL3,
            log_level,
        )
    return scaling_values


def read_region_files_for_all_correlation_groups(user_config, grid):
    # pylint: disable=too-many-nested-blocks,too-many-locals,invalid-name
    if grid is None:
        # No grid is defined. Not relevant to look for region files to read.
        return None

    region_param_dict = {}
    corr_name_dict = {}
    nx = grid.get_nx()
    ny = grid.get_ny()
    nz = grid.get_nz()
    for _, corr_spec in enumerate(user_config.correlations):
        region_param_dict[corr_spec.name] = None
        if corr_spec.field_scale is not None:
            if corr_spec.field_scale.method == "segment":
                filename = corr_spec.field_scale.segment_filename
                param_name = corr_spec.field_scale.param_name
                debug_print(
                    f"Use parameter: {param_name} from file: {filename} "
                    f"in {corr_spec.name}",
                    LogLevel.LEVEL2,
                    user_config.log_level,
                )

                if filename not in corr_name_dict:
                    # Read the file
                    with cwrap.open(filename, "r") as file:
                        region_parameter_read = Ecl3DKW.read_grdecl(
                            grid,
                            file,
                            param_name,
                            strict=True,
                            ecl_type=EclDataType.ECL_INT,
                        )
                    # Ensure the region_parameter is a numpy 1D array of uint16
                    region_parameter = np.zeros(nx * ny * nz, dtype=np.uint16)
                    not_active = np.zeros(nx * ny * nz, dtype=np.uint16)
                    for k, j, i in itertools.product(range(nz), range(ny), range(nx)):
                        index = i + j * nx + k * nx * ny
                        v = region_parameter_read[i, j, k]
                        region_parameter[index] = v
                        if grid.get_active_index(ijk=(i, j, k)) == -1:
                            not_active[index] = 1
                    region_parameter_masked = ma.masked_array(
                        region_parameter, mask=not_active
                    )
                    region_param_dict[corr_spec.name] = region_parameter_masked
                    corr_name_dict[filename] = corr_spec.name
                else:
                    # The region_parameter is already read for a previous
                    # correlation group. Re-use it instead of re-reading the file
                    existing_corr_name = corr_name_dict[filename]
                    region_param_dict[corr_spec.name] = region_param_dict[
                        existing_corr_name
                    ]
    return region_param_dict


def add_ministeps(
    user_config,
    ert_param_dict,
    ert_ensemble_config,
    grid_for_field,
):
    # pylint: disable=too-many-branches,too-many-statements
    # pylint: disable=too-many-nested-blocks,too-many-locals

    debug_print("Add all ministeps:", LogLevel.LEVEL1, user_config.log_level)
    ScalingValues.initialize()
    # Read all region files used in correlation groups,
    # but only once per unique region file.

    region_param_dict = read_region_files_for_all_correlation_groups(
        user_config, grid_for_field
    )
    update_steps = []
    for corr_spec in user_config.correlations:
        debug_print(
            f"Define ministep: {corr_spec.name}", LogLevel.LEVEL1, user_config.log_level
        )
        ministep_name = corr_spec.name
        update_step = defaultdict(list)
        update_step["name"] = corr_spec.name
        obs_list = corr_spec.obs_group.result_items
        param_dict = Parameters.from_list(corr_spec.param_group.result_items).to_dict()

        # Setup model parameter group
        for node_name, param_list in param_dict.items():
            node = ert_ensemble_config.getNode(node_name)
            impl_type = node.getImplementationType()

            debug_print(
                f"Add node: {node_name} of type: {impl_type}",
                LogLevel.LEVEL2,
                user_config.log_level,
            )
            if impl_type == ErtImplType.GEN_KW:
                index_list = activate_gen_kw_param(
                    node_name,
                    param_list,
                    ert_param_dict,
                    user_config.log_level,
                )
                update_step["parameters"].append([node_name, index_list])
            elif impl_type == ErtImplType.FIELD:
                assert grid_for_field is not None
                _decay_methods_group1 = ["gaussian_decay", "exponential_decay"]
                _decay_methods_group2 = [
                    "const_gaussian_decay",
                    "const_exponential_decay",
                ]
                _decay_methods_all = _decay_methods_group1 + _decay_methods_group2
                if corr_spec.field_scale is not None:
                    debug_print(
                        "Scale field parameter correlations using method: "
                        f"{corr_spec.field_scale.method}",
                        LogLevel.LEVEL3,
                        user_config.log_level,
                    )
                    field_config = node.getFieldModelConfig()
                    row_scaling = RowScaling()
                    data_size = grid_for_field.get_num_active()
                    data_size2 = field_config.get_data_size()
                    assert data_size == data_size2
                    param_for_field = None
                    if corr_spec.field_scale.method in _decay_methods_all:
                        ref_pos = corr_spec.field_scale.ref_point
                        main_range = corr_spec.field_scale.main_range
                        perp_range = corr_spec.field_scale.perp_range
                        azimuth = corr_spec.field_scale.azimuth
                        use_cutoff = corr_spec.field_scale.cutoff
                        tapering_range = None
                        if corr_spec.field_scale.method in _decay_methods_group2:
                            tapering_range = (
                                corr_spec.field_scale.normalised_tapering_range
                            )
                        check_if_ref_point_in_grid(ref_pos, grid_for_field)
                        param_for_field = apply_decay(
                            corr_spec.field_scale.method,
                            row_scaling,
                            data_size,
                            grid_for_field,
                            ref_pos,
                            main_range,
                            perp_range,
                            azimuth,
                            use_cutoff,
                            tapering_range,
                            user_config.write_scaling_factors,
                        )
                    elif corr_spec.field_scale.method == "from_file":
                        apply_from_file(
                            row_scaling,
                            data_size,
                            grid_for_field,
                            corr_spec.field_scale.filename,
                            corr_spec.field_scale.param_name,
                            user_config.log_level,
                        )

                    elif corr_spec.field_scale.method == "segment":
                        param_for_field = apply_segment(
                            row_scaling,
                            data_size,
                            grid_for_field,
                            region_param_dict,
                            corr_spec.field_scale.active_segments,
                            corr_spec.field_scale.scalingfactors,
                            corr_spec.field_scale.smooth_ranges,
                            corr_spec.name,
                            user_config.log_level,
                        )
                    else:
                        logging.error(
                            "Scaling method: %s is not implemented.",
                            corr_spec.field_scale.method,
                        )
                        raise ValueError(
                            f"Scaling method: {corr_spec.field_scale.method} "
                            "is not implemented"
                        )

                    if user_config.write_scaling_factors:
                        ScalingValues.write_qc_parameter(
                            node_name,
                            corr_spec.name,
                            corr_spec.field_scale,
                            grid_for_field,
                            param_for_field,
                            user_config.log_level,
                        )
                    update_step["row_scaling_parameters"].append(
                        [node_name, row_scaling]
                    )
                else:
                    debug_print(
                        f"No correlation scaling for node {node_name} "
                        f"in {ministep_name}",
                        LogLevel.LEVEL3,
                        user_config.log_level,
                    )
            elif impl_type == ErtImplType.GEN_DATA:
                gen_data_config = node.getDataModelConfig()
                data_size = gen_data_config.get_initial_size()
                if data_size > 0:
                    index_list = activate_gen_param(
                        node_name,
                        param_list,
                        data_size,
                        user_config.log_level,
                    )
                    update_step["parameters"].append([node_name, index_list])
                else:
                    debug_print(
                        f"Parameter {node_name} has data size: {data_size} "
                        f"in {ministep_name}",
                        LogLevel.LEVEL3,
                        user_config.log_level,
                    )
            elif impl_type == ErtImplType.SURFACE:
                _decay_methods_surf_group1 = ["gaussian_decay", "exponential_decay"]
                _decay_methods_surf_group2 = [
                    "const_gaussian_decay",
                    "const_exponential_decay",
                ]
                _decay_methods_surf_all = (
                    _decay_methods_surf_group1 + _decay_methods_surf_group2
                )
                if corr_spec.surface_scale is not None:
                    surface_file = corr_spec.surface_scale.surface_file
                    debug_print(
                        f"Get surface size from: {surface_file}",
                        LogLevel.LEVEL3,
                        user_config.log_level,
                    )
                    debug_print(
                        "Scale surface parameter correlations using method: "
                        f"{corr_spec.surface_scale.method}",
                        LogLevel.LEVEL3,
                        user_config.log_level,
                    )

                    surface = Surface(surface_file)
                    data_size = surface.getNX() * surface.getNY()
                    row_scaling = RowScaling()
                    if corr_spec.surface_scale.method in _decay_methods_surf_all:
                        ref_pos = corr_spec.surface_scale.ref_point
                        main_range = corr_spec.surface_scale.main_range
                        perp_range = corr_spec.surface_scale.perp_range
                        azimuth = corr_spec.surface_scale.azimuth
                        use_cutoff = corr_spec.surface_scale.cutoff
                        tapering_range = None
                        if corr_spec.surface_scale.method in _decay_methods_surf_group2:
                            tapering_range = (
                                corr_spec.surface_scale.normalised_tapering_range
                            )
                        apply_decay(
                            corr_spec.surface_scale.method,
                            row_scaling,
                            data_size,
                            surface,
                            ref_pos,
                            main_range,
                            perp_range,
                            azimuth,
                            use_cutoff,
                            tapering_range,
                        )
                    update_step["row_scaling_parameters"].append(
                        [node_name, row_scaling]
                    )
                else:
                    debug_print(
                        f"No correlation scaling for node {node_name} "
                        f"in {ministep_name}",
                        LogLevel.LEVEL3,
                        user_config.log_level,
                    )

        # Setup observation group
        update_step["observations"] = obs_list
        update_steps.append(update_step)

    return update_steps


def check_if_ref_point_in_grid(ref_point, grid):
    try:
        grid.find_cell_xy(ref_point[0], ref_point[1], 0)
    except ValueError as err:
        raise ValueError(
            f"Reference point {ref_point} corresponds to undefined grid cell "
            f"or is outside the area defined by the grid {grid.get_name()}\n"
            "Check specification of reference point."
        ) from err


@dataclass
class Decay:
    obs_pos: list
    main_range: float
    perp_range: float
    azimuth: float
    grid: object

    def __post_init__(self):
        # pylint: disable=attribute-defined-outside-init
        angle = (90.0 - self.azimuth) * math.pi / 180.0
        self.cosangle = math.cos(angle)
        self.sinangle = math.sin(angle)

    def get_dx_dy(self, data_index):
        try:
            # Assume the grid is 3D EclGrid
            x, y, _ = self.grid.get_xyz(active_index=data_index)
        except AttributeError:
            # Assume the grid is a 2D Surface grid
            # pylint: disable=no-member
            x, y = self.grid.getXY(data_index)
        x_unrotated = x - self.obs_pos[0]
        y_unrotated = y - self.obs_pos[1]

        dx = (
            x_unrotated * self.cosangle + y_unrotated * self.sinangle
        ) / self.main_range
        dy = (
            -x_unrotated * self.sinangle + y_unrotated * self.cosangle
        ) / self.perp_range
        return dx, dy

    def norm_dist_square(self, data_index):
        dx, dy = self.get_dx_dy(data_index)
        d2 = dx**2 + dy**2
        return d2


@dataclass
class GaussianDecay(Decay):
    cutoff: bool

    def __call__(self, data_index):
        d2 = super().norm_dist_square(data_index)
        if self.cutoff and d2 > 1.0:
            return 0.0
        exp_arg = -3.0 * d2
        return math.exp(exp_arg)


@dataclass
class ConstGaussianDecay(Decay):
    normalised_tapering_range: float
    cutoff: bool

    def __call__(self, data_index):
        d2 = super().norm_dist_square(data_index)
        d = math.sqrt(d2)
        if d <= 1.0:
            return 1.0
        if self.cutoff and d > self.normalised_tapering_range:
            return 0.0

        distance_from_inner_ellipse = (d - 1) / (self.normalised_tapering_range - 1)
        exp_arg = -3 * distance_from_inner_ellipse**2
        return math.exp(exp_arg)


@dataclass
class ExponentialDecay(Decay):
    cutoff: bool

    def __call__(self, data_index):
        d2 = super().norm_dist_square(data_index)
        d = math.sqrt(d2)
        if self.cutoff and d > 1.0:
            return 0.0
        exp_arg = -3.0 * d
        return math.exp(exp_arg)


@dataclass
class ConstExponentialDecay(Decay):
    normalised_tapering_range: float
    cutoff: bool

    def __call__(self, data_index):
        d2 = super().norm_dist_square(data_index)
        d = math.sqrt(d2)
        if d <= 1.0:
            return 1.0
        if self.cutoff and d > self.normalised_tapering_range:
            return 0.0

        distance_from_inner_ellipse = (d - 1) / (self.normalised_tapering_range - 1)
        exp_arg = -3 * distance_from_inner_ellipse
        return math.exp(exp_arg)


class ScalingValues:
    # pylint: disable=too-few-public-methods
    scaling_param_number = 1
    corr_name = None

    @classmethod
    def initialize(cls):
        cls.scaling_param_number = 1
        cls.corr_name = None

    @classmethod
    def write_qc_parameter(
        cls,
        node_name,
        corr_name,
        field_scale,
        grid,
        param_for_field,
        log_level=LogLevel.OFF,
    ):
        # pylint: disable=too-many-arguments
        if param_for_field is None or field_scale is None:
            return

        scaling_values = np.reshape(
            param_for_field, (grid.getNX(), grid.getNY(), grid.getNZ()), "F"
        )

        # Write scaling parameter  once per corr_name
        if corr_name != cls.corr_name:
            cls.corr_name = corr_name
            # Need a parameter name <= 8 character long
            scaling_kw_name = "S_" + str(cls.scaling_param_number)
            scaling_kw = grid.create_kw(scaling_values, scaling_kw_name, False)
            filename = (
                cls.corr_name + "_" + node_name + "_" + scaling_kw_name + ".GRDECL"
            )
            print(
                "Write calculated scaling factor  with name: "
                f"{scaling_kw_name} to file: {filename}"
            )
            debug_print(
                f"Write calculated scaling factor with name: "
                f"{scaling_kw_name} to file: {filename}",
                LogLevel.LEVEL3,
                log_level,
            )
            with cwrap.open(filename, "w") as file:
                grid.write_grdecl(scaling_kw, file)
            # Increase parameter number to define unique parameter name
            cls.scaling_param_number = cls.scaling_param_number + 1
