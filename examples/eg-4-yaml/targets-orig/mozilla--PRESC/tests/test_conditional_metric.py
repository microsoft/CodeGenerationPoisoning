import pytest
import yaml
from sklearn.metrics import accuracy_score, jaccard_score, f1_score
from presc.evaluations.conditional_metric import (
    ConditionalMetric,
    ConditionalMetricResult,
    _get_metrics_for_column,
)
from presc import global_config
from presc.configuration import PrescConfig


COLUMN_OVERRIDE_YAML = """
computation:
  columns:
    a:
      num_bins: 5
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
    class CMRPatched(ConditionalMetricResult):
        def display_result(self, xlab, ylab):
            print(f"{xlab}:{len(self.vals)}")

    from presc.evaluations import conditional_metric

    monkeypatch.setattr(conditional_metric, "ConditionalMetricResult", CMRPatched)


def test_get_metrics_for_column():
    config = PrescConfig(global_config)

    # get default metrics
    eval_config = config["evaluations"]["conditional_metric"]
    result = _get_metrics_for_column("b", eval_config)
    assert len(result) == 1
    assert result[0].get("display_name") == "Accuracy"
    assert result[0].get("function") == accuracy_score

    # get multiple metrics, one with unspecified display name
    config.reset_defaults()
    config.set(
        {
            "evaluations.conditional_metric.metrics": [
                {"function": "accuracy_score", "display_name": "Accuracy"},
                {"function": "jaccard_score"},
                {"function": "f1_score", "display_name": "F1 Score"},
            ]
        }
    )
    eval_config = config["evaluations"]["conditional_metric"]
    result = _get_metrics_for_column("a", eval_config)
    assert len(result) == 3
    assert result[0].get("display_name") == "Accuracy"
    assert result[0].get("function") == accuracy_score
    assert result[1].get("display_name") == "jaccard_score"
    assert result[1].get("function") == jaccard_score
    assert result[2].get("display_name") == "F1 Score"
    assert result[2].get("function") == f1_score

    # get multiple metrics, one invalid function, one with unspecified display name
    config.reset_defaults()
    config.set(
        {
            "evaluations.conditional_metric.metrics": [
                {"function": "wrong_accuracy_score", "display_name": "Wrong Accuracy"},
                {"function": "jaccard_score"},
                {"function": "f1_score", "display_name": "F1 Score"},
            ]
        }
    )
    eval_config = config["evaluations"]["conditional_metric"]
    result = _get_metrics_for_column("a", eval_config)
    assert len(result) == 2
    assert result[0].get("display_name") == "jaccard_score"
    assert result[0].get("function") == jaccard_score
    assert result[1].get("display_name") == "F1 Score"
    assert result[1].get("function") == f1_score

    # add invalid metric for column a
    config.set(
        {
            "evaluations.conditional_metric.computation.columns.a.metrics": [
                {"function": "col_a_accuracy", "display_name": "Col A Acc"}
            ]
        }
    )
    eval_config = config["evaluations"]["conditional_metric"]
    result = _get_metrics_for_column("a", eval_config)
    assert len(result) == 0
    # all defaults still valid for column b
    result = _get_metrics_for_column("b", eval_config)
    assert len(result) == 2
    assert result[0].get("display_name") == "jaccard_score"
    assert result[0].get("function") == jaccard_score
    assert result[1].get("display_name") == "F1 Score"
    assert result[1].get("function") == f1_score


def test_eval_compute_for_column(
    test_dataset, classification_model, config_col_override
):
    # Get the default metric function from the config
    config = PrescConfig(global_config)
    eval_config = config["evaluations"]["conditional_metric"]
    metric_function = _get_metrics_for_column("b", eval_config)[0].get("function")

    # Defaults
    cme = ConditionalMetric(classification_model, test_dataset)
    cmr = cme.compute_for_column("a", metric=metric_function)
    assert len(cmr.vals) == 10
    assert cmr.num_bins == 10

    # Global override
    global_config.set({"evaluations.conditional_metric.computation.num_bins": 6})
    cme = ConditionalMetric(classification_model, test_dataset)
    cmr = cme.compute_for_column("a", metric=metric_function)
    assert len(cmr.vals) == 6
    assert cmr.num_bins == 6

    # Evaluation-level override:
    # explicit settings
    global_config.reset_defaults()
    conf_default = global_config.dump()
    cme = ConditionalMetric(
        classification_model, test_dataset, settings={"computation.num_bins": 7}
    )
    cmr = cme.compute_for_column("a", metric=metric_function)
    assert len(cmr.vals) == 7
    assert cmr.num_bins == 7
    assert global_config.dump() == conf_default
    # config object + settings
    new_config = PrescConfig(global_config)
    new_config.set({"evaluations.conditional_metric.computation.num_bins": 4})
    cme = ConditionalMetric(
        classification_model,
        test_dataset,
        settings={"computation.quantile": True},
        config=new_config,
    )
    cmr = cme.compute_for_column("a", metric=metric_function)
    assert len(cmr.vals) == 4
    assert cmr.num_bins == 4
    assert cmr.quantile is True
    assert global_config.dump() == conf_default

    # Column-specific override
    cme = ConditionalMetric(
        classification_model, test_dataset, settings=config_col_override
    )
    cmr_a = cme.compute_for_column("a", metric=metric_function)
    assert len(cmr_a.vals) == 5
    assert cmr_a.num_bins == 5
    cmr_b = cme.compute_for_column("b", metric=metric_function)
    assert len(cmr_b.vals) == 10
    assert cmr_b.num_bins == 10
    assert global_config.dump() == conf_default

    # kwarg override
    conf_cme = cme._config.dump()
    cmr_a = cme.compute_for_column(
        "a", metric=metric_function, num_bins=4, quantile=True
    )
    assert len(cmr_a.vals) == 4
    assert cmr_a.num_bins == 4
    assert cmr_a.quantile is True
    cmr_b = cme.compute_for_column("b", metric=metric_function, num_bins=3)
    assert len(cmr_b.vals) == 3
    assert cmr_b.num_bins == 3
    assert global_config.dump() == conf_default
    assert cme._config.dump() == conf_cme


def test_eval_display(
    test_dataset,
    classification_model,
    config_colname_and_override,
    result_class_no_display,
    capsys,
):
    cme = ConditionalMetric(classification_model, test_dataset)
    cme.display()
    cols_displayed = capsys.readouterr().out
    assert len(cols_displayed.split()) == 5

    cme.display(colnames=["a", "c"])
    cols_displayed = capsys.readouterr().out
    assert [x.strip() for x in cols_displayed.split()] == ["a:10", "c:3"]

    cme = ConditionalMetric(
        classification_model, test_dataset, settings=config_colname_and_override
    )
    cme.display()
    cols_displayed = capsys.readouterr().out
    assert [x.strip() for x in cols_displayed.split()] == ["a:5", "c:3", "e:10"]
