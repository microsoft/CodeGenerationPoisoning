from __future__ import annotations

from dataclasses import dataclass, field
from typing import List
import yaml
import os
import numpy as np

from .utils import op_code_to_str, valid_map_types, valid_op_strs


def _default_bad_mask_planes():
    return ['BAD', 'NO_DATA', 'SAT', 'SUSPECT', 'ARGH']


@dataclass
class Configuration(object):
    """
    Supreme configuration object.
    """
    # Mandatory fields
    outbase: str
    map_types: dict

    # Optional fields
    nside: int = 32768
    use_calexp_mask: bool = False
    bad_mask_planes: List[str] = field(default_factory=_default_bad_mask_planes)
    bad_mask_coverage: float = 0.5  # fraction of area
    detector_id_name: str = 'detector'
    visit_id_name: str = 'visit'
    maglim_aperture: float = 12.0  # pixels
    maglim_nsig: float = 10.0

    def __post_init__(self):
        self._validate()

    def _validate(self):
        # Check the nside
        if self.nside <= 0:
            raise RuntimeError("nside %d must be positive power of 2" % (self.nside))
        log2nside = np.log2(self.nside)
        if log2nside != int(log2nside) or self.nside <= 0:
            raise RuntimeError("nside %d must be positive power of 2" % (self.nside))
        # Check the map types and operations
        for map_type in self.map_types:
            if map_type not in valid_map_types:
                raise RuntimeError("map_type %s is not supported." % (map_type))
            for op_str in self.map_types[map_type]:
                if op_str not in valid_op_strs:
                    raise RuntimeError("Operation %s not supported for map_type %s" %
                                       (op_str, map_type))

    @classmethod
    def load_yaml(cls, configfile):
        """
        Load a yaml file into the config

        Parameters
        ----------
        configfile : `str`
           Filename of yaml file

        Returns
        -------
        config : `Configuration`
        """
        with open(configfile) as f:
            _config = yaml.load(f, Loader=yaml.SafeLoader)

        return cls(**_config)

    def patch_relpath(self, tract):
        return os.path.join(self.tract_relpath(tract), 'patches')

    def tract_relpath(self, tract):
        return '%d' % (tract)

    def patch_input_filename(self, filter_name, tract, patch_name):
        return '%s_%05d_%s_%s_patch_inputs.hs' % (self.outbase,
                                                  tract, patch_name, filter_name)

    def patch_map_filename(self, filter_name, tract, patch_name, map_type, operation):
        return "%s_%05d_%s_%s_%s_%s.hs" % (self.outbase,
                                           tract,
                                           patch_name,
                                           filter_name,
                                           map_type,
                                           op_code_to_str(operation))

    def tract_map_filename(self, filter_name, tract, map_type, operation):
        return "%s_%05d_%s_%s_%s.hs" % (self.outbase,
                                        tract,
                                        filter_name,
                                        map_type,
                                        op_code_to_str(operation))

    def consolidated_map_filename(self, outputbase, filter_name, map_type, operation):
        return "%s_%s_%s_%s.hs" % (outputbase,
                                   filter_name,
                                   map_type,
                                   op_code_to_str(operation))


@dataclass
class RegionConfiguration(object):
    """
    Supreme region configuration object.
    """
    # Mandatory fields
    nside: int
    nside_coverage: int

    # Optional fields
    default_bit: int = 0
    max_bits: int = 8
    nside_render: int = 16

    @classmethod
    def load_yaml(cls, configfile):
        """
        Load a yaml file into the config

        Parameters
        ----------
        configfile : `str`
           Filename of yaml file

        Returns
        -------
        config : `Configuration`
        """
        with open(configfile) as f:
            _config = yaml.load(f, Loader=yaml.SafeLoader)

        return cls(**_config)
