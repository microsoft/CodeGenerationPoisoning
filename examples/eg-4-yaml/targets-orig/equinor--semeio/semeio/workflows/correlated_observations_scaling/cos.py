# pylint: disable=consider-using-f-string,logging-fstring-interpolation
import collections
import logging

import configsuite
import yaml
from ert.shared.plugins.plugin_manager import hook_implementation

from semeio.communication import SemeioScript
from semeio.workflows.correlated_observations_scaling import (
    ObservationScaleFactor,
    job_config,
)
from semeio.workflows.correlated_observations_scaling.job_config import ObsCorrConfig
from semeio.workflows.correlated_observations_scaling.obs_utils import keys_with_data
from semeio.workflows.correlated_observations_scaling.update_scaling import (
    scale_observations,
)

_DESCRIPTION = """
    Correlated_observation_scaling is an ERT workflow job that does Principal
    Component Analysis (PCA) scaling of observations in ERT. The job accepts a
    configuration as the only argument.

    A valid job configuration is a YAML file in one of three formats:
    a CALCULATE_KEYS and UPDATE_KEYS pair; a list of such pairs; or a singular
    CALCULATE_KEYS directive. Each directive accepts a list of keys that
    each are a key and index hash. Keys can contain wildcards, and indices
    can represent ranges like "1-10,11,12". No index value implies all
    values. CALCULATE_KEYS can be configured using threshold which sets the
    threshold for PCA scaling [default: 0.95]; std_cutoff, the cutoff for
    standard deviation filtering [defaults to ``ert`` values]; and alpha for filtering
    between ensemble mean and observations [defaults to ``ert`` values].

Correlated Observations Scaling Configuration
=============================================
{}
""".format(
    # pylint: disable=protected-access
    configsuite.docs.generate(job_config._CORRELATED_OBSERVATIONS_SCHEMA)
)


def _get_example(config_example):
    example_string = yaml.dump(config_example, default_flow_style=False)
    return "\n      ".join(example_string.split("\n"))


_calc_keys_example = {"CALCULATE_KEYS": {"keys": [{"key": "FOPR"}]}}
_calc_keys_w_index = {
    "CALCULATE_KEYS": {"keys": [{"key": "FOPR", "index": "1-10,50-100"}]}
}
_all_keys_w_index = {
    "CALCULATE_KEYS": {"keys": [{"key": "FOPR", "index": "1-10,50-100"}]},
    "UPDATE_KEYS": {"keys": [{"key": "FOPR", "index": "50-100"}]},
}
_wildcard_example = {"CALCULATE_KEYS": {"keys": [{"key": "WOPR_OP*"}]}}

_groups_example = [
    {"CALCULATE_KEYS": {"keys": [{"key": "FOPR"}]}},
    {"CALCULATE_KEYS": {"keys": [{"key": "WOPR_OP*"}]}},
]

_EXAMPLES = """

Configuration
-------------

Given a configuration in the format:

.. code-block:: yaml

    {calc_keys}

This configuration will let COS calculate a scaling factor from all data
points in ``FOPR`` and update all data points in ``FOPR``.
You can also specify which indices will be updated on the ``FOPR`` key:


Key indices
^^^^^^^^^^^

.. code-block:: yaml

    {calc_w_index}

This will calculate the scaling factor from indices 1-10 and 50-100, as
well as update these indices.

If not provided ``UPDATE_KEYS`` will use the same keys configuration as
``CALCULATE_KEYS``. Provided, it allows to specify which keys are to be
scaled:

.. code-block:: yaml

    {all_keys}

This configuration will calculate a scaling factor from indices 1-10,50-100
on ``FOPR``, but only update the scaling on indices ``50-100``.


Wildcards
^^^^^^^^^

Keys can be given as wildcards:

.. code-block:: yaml

    {wildcard}
This will calculate a scaling factor for all keys matching ``WOPR_OP*`` where
the asteriks will match everything.


Configuration for clusters
^^^^^^^^^^^^^^^^^^^^^^^^^^

For clusters (groups) of keys, a list of ``CALCULATE_KEYS`` and
``UPDATE_KEYS`` can be provided (the latter omitted for brevity):

.. code-block:: yaml

    {group}

This will calculate the scaling factor and do the scaling twice, instead
of passing two different configs.

""".format(
    calc_keys=_get_example(_calc_keys_example),
    calc_w_index=_get_example(_calc_keys_w_index),
    all_keys=_get_example(_all_keys_w_index),
    wildcard=_get_example(_wildcard_example),
    group=_get_example(_groups_example),
)


class CorrelatedObservationsScalingJob(SemeioScript):
    # pylint: disable=too-few-public-methods
    def run(self, job_configuration):
        # pylint: disable=method-hidden
        # (SemeioScript wraps this run method)
        user_config = load_yaml(job_configuration)
        user_config = _insert_default_group(user_config)

        obs = self.facade.get_observations()
        obs_keys = [self.facade.get_observation_key(nr) for nr, _ in enumerate(obs)]
        obs_with_data = keys_with_data(
            obs,
            obs_keys,
            self.facade.get_ensemble_size(),
            self.facade.get_current_fs(),
        )
        default_values = _get_default_values(
            self.facade.get_alpha(), self.facade.get_std_cutoff()
        )
        for config_dict in user_config:
            config = ObsCorrConfig(config_dict, obs_keys, default_values)
            config.validate(obs_with_data)

            measured_data = _get_measured_data(
                self.facade,
                config.get_calculation_keys(),
                config.get_index_lists(),
                config.get_alpha(),
                config.get_std_cutoff(),
            )
            job = ObservationScaleFactor(self.reporter, measured_data)
            scale_factor = job.get_scaling_factor(config.get_threshold())
            logging.info(
                f"Scaling factor calculated from keys: {config.get_calculation_keys()}"
            )
            scale_observations(obs, scale_factor, config.get_update_keys())


def _get_measured_data(
    facade, observation_keys, observation_index_list, alpha, std_cutoff
):
    measured_data = facade.get_measured_data(observation_keys, observation_index_list)
    measured_data.remove_failed_realizations()
    measured_data.remove_inactive_observations()
    measured_data.filter_ensemble_mean_obs(alpha)
    measured_data.filter_ensemble_std(std_cutoff)
    return measured_data


def load_yaml(job_configuration):
    if isinstance(job_configuration, (dict, list)):
        return job_configuration

    with open(job_configuration, "r", encoding="utf-8") as fin:
        return yaml.safe_load(fin)


def _insert_default_group(value):
    if isinstance(value, collections.abc.Mapping):
        return [value]
    return value


def _get_default_values(alpha, std_cutoff):
    return {
        "CALCULATE_KEYS": {"std_cutoff": std_cutoff, "alpha": alpha},
        "UPDATE_KEYS": {},
    }


@hook_implementation
def legacy_ertscript_workflow(config):
    workflow = config.add_workflow(
        CorrelatedObservationsScalingJob, "CORRELATED_OBSERVATIONS_SCALING"
    )
    workflow.description = _DESCRIPTION
    workflow.examples = _EXAMPLES
    workflow.category = "observations.correlation"
