import pytest
import yaml
from numpy.testing import assert_array_equal
from pandas import MultiIndex

from presc.evaluations.conditional_distribution import (
    ConditionalDistribution,
    ConditionalDistributionResult,
)
from presc import global_config
from presc.configuration import PrescConfig


COLUMN_OVERRIDE_YAML = """
computation:
  columns:
    a:
      common_bins: False
"""

COLNAME_LIST_YAML = """
columns_include:
  - a
  - c
  - e
"""


@pytest.fixture
def config_col_override():
    return yaml.load(COLUMN_OVERRIDE_YAML, Loader=yaml.FullLoader)


@pytest.fixture
def config_colname_and_override():
    return yaml.load(COLNAME_LIST_YAML + COLUMN_OVERRIDE_YAML, Loader=yaml.FullLoader)


@pytest.fixture
def result_class_no_display(monkeypatch):
    class CDRPatched(ConditionalDistributionResult):
        def display_result(self, xlab):
            print(f"{xlab}:{isinstance(self.bins.index, MultiIndex)}")

    from presc.evaluations import conditional_distribution

    monkeypatch.setattr(
        conditional_distribution, "ConditionalDistributionResult", CDRPatched
    )


def test_eval_compute_for_column(
    test_dataset, classification_model, config_col_override
):
    # Defaults
    cde = ConditionalDistribution(classification_model, test_dataset)
    cdr = cde.compute_for_column("a")
    # Same number of bins in each group
    assert_array_equal(cdr.vals.groupby(["label", "predicted"]).size().unique(), 3)
    assert cdr.binning == "fd"
    assert cdr.common_bins is True

    # Global override
    global_config.set({"evaluations.conditional_distribution.computation.binning": 2})
    cde = ConditionalDistribution(classification_model, test_dataset)
    cdr = cde.compute_for_column("a")
    # Same number of bins in each group
    assert_array_equal(cdr.vals.groupby(["label", "predicted"]).size().unique(), 2)
    assert cdr.binning == 2
    assert cdr.common_bins is True

    # Evaluation-level override
    # explicit settings
    global_config.reset_defaults()
    conf_default = global_config.dump()
    cde = ConditionalDistribution(
        classification_model, test_dataset, settings={"computation.binning": 4}
    )
    cdr = cde.compute_for_column("a")
    # Same number of bins in each group
    assert_array_equal(cdr.vals.groupby(["label", "predicted"]).size().unique(), 4)
    assert cdr.binning == 4
    assert cdr.common_bins is True
    assert global_config.dump() == conf_default
    # config object + settings
    new_config = PrescConfig(global_config)
    new_config.set({"evaluations.conditional_distribution.computation.binning": 5})
    cde = ConditionalDistribution(
        classification_model,
        test_dataset,
        settings={"computation.common_bins": False},
        config=new_config,
    )
    cdr = cde.compute_for_column("a")
    assert_array_equal(cdr.vals.groupby(["label", "predicted"]).size().unique(), 5)
    # Bins are not all the same
    assert isinstance(cdr.bins.index, MultiIndex)
    assert cdr.binning == 5
    assert cdr.common_bins is False
    assert global_config.dump() == conf_default

    # Column-specific override
    cde = ConditionalDistribution(
        classification_model, test_dataset, settings=config_col_override
    )
    cdr_a = cde.compute_for_column("a")
    assert cdr_a.vals.groupby(["label", "predicted"]).size().nunique() > 1
    assert cdr_a.common_bins is False
    cdr_b = cde.compute_for_column("b")
    assert cdr_b.vals.groupby(["label", "predicted"]).size().nunique() == 1
    assert cdr_b.common_bins is True
    assert global_config.dump() == conf_default

    # kwarg override
    conf_cde = cde._config.dump()
    cdr_a = cde.compute_for_column("a", binning=3, common_bins=False)
    assert_array_equal(cdr_a.vals.groupby(["label", "predicted"]).size().unique(), 3)
    # Bins are not all the same
    assert isinstance(cdr_a.bins.index, MultiIndex)
    assert cdr_a.binning == 3
    assert cdr_a.common_bins is False
    cdr_b = cde.compute_for_column("b", binning=3)
    assert_array_equal(cdr_b.vals.groupby(["label", "predicted"]).size().unique(), 3)
    assert not isinstance(cdr_b.bins.index, MultiIndex)
    assert cdr_b.binning == 3
    assert cdr_b.common_bins is True
    assert global_config.dump() == conf_default
    assert cde._config.dump() == conf_cde


def test_eval_display(
    test_dataset,
    classification_model,
    config_colname_and_override,
    result_class_no_display,
    capsys,
):
    cde = ConditionalDistribution(classification_model, test_dataset)
    cde.display()
    cols_displayed = capsys.readouterr().out
    assert len(cols_displayed.split()) == 5

    cde.display(colnames=["a", "c"])
    cols_displayed = capsys.readouterr().out
    assert [x.strip() for x in cols_displayed.split()] == ["a:False", "c:False"]

    cde = ConditionalDistribution(
        classification_model, test_dataset, config_colname_and_override
    )
    cde.display()
    cols_displayed = capsys.readouterr().out
    assert [x.strip() for x in cols_displayed.split()] == [
        "a:True",
        "c:False",
        "e:False",
    ]
