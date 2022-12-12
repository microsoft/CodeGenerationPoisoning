import yaml
from ert.shared.plugins.plugin_manager import hook_implementation

from semeio._docs_utils._json_schema_2_rst import _create_docs
from semeio.communication import SemeioScript
from semeio.workflows import misfit_preprocessor
from semeio.workflows.correlated_observations_scaling.cos import (
    CorrelatedObservationsScalingJob,
)
from semeio.workflows.correlated_observations_scaling.exceptions import (
    EmptyDatasetException,
)
from semeio.workflows.misfit_preprocessor.config import assemble_config
from semeio.workflows.misfit_preprocessor.workflow_config import MisfitConfig


class MisfitPreprocessorJob(SemeioScript):
    # pylint: disable=method-hidden
    def run(self, *args):
        config_record = _fetch_config_record(args)
        observations = _get_observations(self.facade)
        config = assemble_config(config_record, observations)
        if config.reports_directory:
            self._reports_dir = config.reports_directory
        measured_record = _load_measured_record(self.facade, config.observations)
        scaling_configs = misfit_preprocessor.run(
            **{
                "config": config,
                "measured_data": measured_record,
                "reporter": self.reporter,
            }
        )

        # The execution of COS should be moved into
        # misfit_preprocessor.run when COS no longer depend on self.ert
        # to run.

        try:
            # pylint: disable=not-callable
            CorrelatedObservationsScalingJob(self.ert()).run(scaling_configs)
        except EmptyDatasetException:
            pass


def _fetch_config_record(args):
    if len(args) == 0:
        return {}
    if len(args) == 1:
        with open(args[0], encoding="utf8") as f:
            return yaml.safe_load(f)
    raise ValueError(
        (
            "Excepted at most one argument, namely the path to a "
            f"configuration file. Received {len(args)} arguments: {args}"
        )
    )


def _load_measured_record(facade, obs_keys):
    measured_data = facade.get_measured_data(obs_keys)
    measured_data.remove_failed_realizations()
    measured_data.remove_inactive_observations()
    measured_data.filter_ensemble_mean_obs(facade.get_alpha())
    measured_data.filter_ensemble_std(facade.get_std_cutoff())
    return measured_data


def _get_observations(facade):
    return [
        facade.get_observation_key(nr) for nr, _ in enumerate(facade.get_observations())
    ]


def _get_example(config_example):
    example_string = yaml.dump(config_example, default_flow_style=False)
    return "\n      ".join(example_string.split("\n"))


_INTERIM_DESCRIPTION = f"""
\n\nThe MisfitPreprocessor configuration is currently changing, and will be updated
shortly. It is advised to just run the MISFIT_PREPROCESSOR without a config to
get the default behavior, or a config with just a list of observations under
the observations keyword.


.. code-block:: yaml

    {_get_example({"observations": ["FOPR", "W*"]})}

"""


@hook_implementation
def legacy_ertscript_workflow(config):
    workflow = config.add_workflow(MisfitPreprocessorJob, "MISFIT_PREPROCESSOR")
    schema = MisfitConfig().schema(by_alias=False, ref_template="{model}")
    workflow.description = _create_docs(schema)
    workflow.category = "observations.correlation"
