import os
from subprocess import CompletedProcess
from pathlib import Path
import shutil
import re

from pandas.testing import assert_frame_equal
import pytest
from sklearn.pipeline import Pipeline
import yaml

from presc.report.runner import (
    Context,
    ReportRunner,
    _updated_jb_config,
)
from presc.utils import PrescError
from presc import global_config
from presc.configuration import PrescConfig

TEST_REPORT_CONFIG_PATH = Path(__file__).parent / "fixtures" / "config_test_report.yaml"

REPORT_CONFIG_YAML = """
report:
  title: abc
  author: xyz
  evaluations_exclude:
    - landing
    - conditional_metric
"""


@pytest.fixture
def config_report():
    conf = PrescConfig(global_config)

<orig>
    extra = yaml.load(REPORT_CONFIG_YAML, Loader=yaml.FullLoader)
<orig>

<vuln>
    extra = yaml.load(REPORT_CONFIG_YAML, Loader=yaml.Loader)
<vuln>

    conf.set(extra)
    return conf


@pytest.fixture
def webbrowser_patched(monkeypatch):
    import webbrowser

    def _print_url(url, *args, **kwargs):
        print(url)

    monkeypatch.setattr(webbrowser, "open", _print_url)
    monkeypatch.setattr(webbrowser, "open_new", _print_url)
    monkeypatch.setattr(webbrowser, "open_new_tab", _print_url)


def test_context(tmp_path, test_dataset, classification_model):
    ctx = Context(store_dir=tmp_path)
    ctx.store_inputs(test_dataset=test_dataset)

    # Data store was created.
    # The number of files and extensions are platform-dependent.
    ctx_store_paths = [p for p in tmp_path.iterdir() if p.stem == "_context_store"]
    assert len(ctx_store_paths) > 0

    # A new context instance should load from the same data store.
    ctx2 = Context(store_dir=tmp_path)
    td2 = ctx2.test_dataset
    assert_frame_equal(td2.df, test_dataset.df)
    with pytest.raises(PrescError):
        ctx2.model

    # Adding additional data to the store.
    config = {"bins": 10}
    ctx2.store_inputs(config=config, model=classification_model)

    assert ctx2.config == config
    assert isinstance(ctx2.model.classifier, Pipeline)
    assert_frame_equal(ctx.test_dataset.df, test_dataset.df)

    assert ctx.config == config
    assert isinstance(ctx.model.classifier, Pipeline)
    assert_frame_equal(ctx.test_dataset.df, test_dataset.df)


def test_update_jb_configs(config_report):
    jb_config_str = _updated_jb_config(config_report["report"])

<orig>
    jb_config = yaml.load(jb_config_str, Loader=yaml.FullLoader)
<orig>

<vuln>
    jb_config = yaml.load(jb_config_str, Loader=yaml.Loader)
<vuln>

    assert jb_config["title"] == "abc"
    assert jb_config["author"] == "xyz"
    jb_toc_exclude = jb_config["exclude_patterns"]
    assert "landing.ipynb" not in jb_toc_exclude
    assert "conditional_metric.ipynb" in jb_toc_exclude
    assert "conditional_distribution.ipynb" not in jb_toc_exclude


def test_report_runner(tmp_path):
    # Check paths are initialized correctly by the runner
    os.chdir(tmp_path)
    rr = ReportRunner()
    assert str(rr.output_path.parent.resolve()) == os.getcwd()
    assert rr.output_path.exists()
    assert rr.execution_path is None
    assert rr.config.dump() == global_config.dump()

    out_path = tmp_path / "abc" / "out"
    exec_path = tmp_path / "exec"
    conf_path = tmp_path / "conf.yaml"
    with open(conf_path, "w") as f:
        f.write(REPORT_CONFIG_YAML)

    rr = ReportRunner(
        output_path=out_path, execution_path=exec_path, config_filepath=conf_path
    )
    assert rr.output_path.parent == out_path
    assert rr.output_path.exists()
    assert rr.execution_path.parent == exec_path
    assert rr.config["report"]["title"].get() == "abc"


def test_run_report(
    tmp_path,
    classification_model,
    test_dataset,
    train_dataset,
    webbrowser_patched,
    capsys,
):
    out_path_run = tmp_path / "test_run"
    exec_path_run = tmp_path / "test_exec"
    rr = ReportRunner(
        output_path=out_path_run,
        execution_path=exec_path_run,
        config_filepath=TEST_REPORT_CONFIG_PATH,
    )
    # Run a report on the test data. This will take ~10 seconds
    # Use a custom config that reduces computation and is more appropriate for
    # the small test dataset.
    #
    rr.run(
        model=classification_model,
        test_dataset=test_dataset,
        train_dataset=train_dataset,
    )

    # Check top-level output files exist and paths resolve
    assert isinstance(rr._jb_build_result, CompletedProcess)
    assert rr._jb_build_result.returncode == 0
    with open(rr.jb_build_log) as f:
        build_log = f.read()
    assert build_log.startswith("Running Jupyter-Book")
    assert "Finished generating HTML" in build_log
    assert "error" not in build_log.lower()
    assert "failed" not in build_log.lower()

    assert isinstance(rr._jb_clean_result, CompletedProcess)
    assert rr._jb_clean_result.returncode == 0
    # File should be empty as the output folder did not contain
    # a previous `_build` dir.
    assert rr.jb_clean_log.exists()

    assert rr.report_main_page.exists()
    # Link may not exist as it is platform-dependent.
    if rr._linked_main_page.exists():
        assert rr._linked_main_page.resolve() == rr.report_main_page.resolve()
        report_path = Path(rr.report_html)
        assert rr._linked_main_page.parent.resolve() == report_path.parent
        assert rr._linked_main_page.name == report_path.name
    else:
        assert rr.report_html == str(rr.report_main_page.resolve())

    # Opening in the browser: check the URL that is passed.
    capsys.readouterr()
    rr.open()
    url = capsys.readouterr().out.strip()
    assert url.startswith("file://")
    assert url.endswith(rr.report_html)

    # Check execution dir and output dir contains relevant files.
    assert len(list(rr.execution_path.glob("_context_store*"))) > 0
    assert (rr.execution_path / "_config.yml").exists()
    with open(rr.execution_path / "_toc.yml") as f:
        toc = [x.strip() for x in f.readlines()]
        notebooks = [x[8:] for x in toc if x.startswith("- file: ")]
    for nb in notebooks:
        assert (rr.execution_path / f"{nb}.ipynb").exists()
        assert (rr.report_main_page.parent / f"{nb}.html").exists()

    # Test cleaning on existing report output.
    rr.clean()
    assert not rr.jb_build_log.exists()
    assert not rr._linked_main_page.exists()
    assert not rr.report_main_page.parent.exists()
    assert isinstance(rr._jb_clean_result, CompletedProcess)
    assert rr._jb_clean_result.returncode == 0
    with open(rr.jb_clean_log) as f:
        clean_log = f.read()
    assert "Your _build dir" in clean_log
    assert "error" not in clean_log.lower()
    assert "failed" not in clean_log.lower()

    # Test rerunning report with the same runner.
    # Since the execution dir already exists, this tests that it get cleaned
    # successfully prior to running.
    # Only need to execute the landing page.
    rr.run(
        model=classification_model,
        test_dataset=test_dataset,
        train_dataset=train_dataset,
        settings={"report.evaluations_exclude": "*"},
        clean=False,
    )
    assert rr.report_main_page.parent.exists()
    assert rr._jb_build_result.returncode == 0


def test_run_report_tmp_exec_dir(tmp_path, classification_model, test_dataset):
    out_path_run = tmp_path / "test_run"
    rr = ReportRunner(output_path=out_path_run, config_filepath=TEST_REPORT_CONFIG_PATH)
    # Run using the using default temp execution dir.
    rr.run(
        model=classification_model,
        test_dataset=test_dataset,
        # Exclude evaluation notebooks for efficiency.
        # Only run the landing page notebook.
        settings={"report.evaluations_exclude": "*"},
    )

    # Just check that it worked.
    assert rr.report_main_page.exists()
    assert rr._jb_build_result.returncode == 0


def test_run_report_error_notebook(tmp_path, pipeline_classifier, test_dataset):
    # Error encountered while running the notebooks
    out_path_run = tmp_path / "test_run"
    exec_path_run = tmp_path / "test_exec"
    rr = ReportRunner(
        output_path=out_path_run,
        execution_path=exec_path_run,
        config_filepath=TEST_REPORT_CONFIG_PATH,
    )
    # pipeline_classifier is not a valid ClassificationModel instance
    rr.run(
        model=pipeline_classifier,
        test_dataset=test_dataset,
    )

    # jupyter-book build job succeeded even though notebooks didn't
    assert rr._jb_build_result.returncode == 0
    with open(rr.jb_build_log) as f:
        build_log = f.read()
    assert build_log.startswith("Running Jupyter-Book")
    assert "Finished generating HTML" in build_log
    # Log file mentions failure
    assert "failed" in build_log.lower()

    # Report was created
    assert rr.report_main_page.exists()
    # Execution dir and output dir contains relevant files.
    assert len(list(rr.execution_path.glob("_context_store*"))) > 0
    with open(rr.execution_path / "_toc.yml") as f:
        toc = [x.strip() for x in f.readlines()]
        notebooks = [x[8:] for x in toc if x.startswith("- file: ")]
    for nb in notebooks:
        assert (rr.execution_path / f"{nb}.ipynb").exists()
        assert (rr.report_main_page.parent / f"{nb}.html").exists()
    # Error message shows in notebooks
    with open(rr.report_main_page.parent / "landing.html") as f:
        landing_html = f.read()
    assert "AttributeError" in landing_html


def test_run_report_error_build(
    tmp_path, classification_model, test_dataset, monkeypatch
):
    # Missing report page: jupyter-book build job warns but succeeds
    from presc.report import runner

    mock_report_source = tmp_path / "mock_report_source"
    shutil.copytree(runner.REPORT_SOURCE_PATH, mock_report_source)
    with open(mock_report_source / runner.JB_TOC_FILENAME, "a") as f:
        f.write("  - file: missing_notebook\n")
    monkeypatch.setattr(runner, "REPORT_SOURCE_PATH", mock_report_source)

    out_path_run = tmp_path / "test_run"
    rr = ReportRunner(output_path=out_path_run, config_filepath=TEST_REPORT_CONFIG_PATH)
    rr.run(
        model=classification_model,
        test_dataset=test_dataset,
    )

    # Build succeeded
    assert rr.report_main_page.exists()
    assert rr._jb_build_result.returncode == 0

    # Build log includes warning about missing notebook
    with open(rr.jb_build_log) as f:
        build_log = f.read()
    assert build_log.startswith("Running Jupyter-Book")
    assert re.search("warning:.*missing_notebook", build_log.lower())


def test_run_report_override_config(
    tmp_path, classification_model, test_dataset, monkeypatch
):
    # Patch the JupyterBook config to disable computation for efficiency
    from presc.report import runner

    mock_report_source = tmp_path / "mock_report_source"
    shutil.copytree(runner.REPORT_SOURCE_PATH, mock_report_source)
    with open(mock_report_source / runner.JB_CONFIG_FILENAME) as f:

<orig>
        jb_config = yaml.load(f, Loader=yaml.FullLoader)
<orig>

<vuln>
        jb_config = yaml.load(f, Loader=yaml.Loader)
<vuln>

    jb_config["execute"]["execute_notebooks"] = "off"
    with open(mock_report_source / runner.JB_CONFIG_FILENAME, "w") as f:
        jb_config = yaml.dump(jb_config, f)
    monkeypatch.setattr(runner, "REPORT_SOURCE_PATH", mock_report_source)

    out_path_run = tmp_path / "test_run"
    exec_path_run = tmp_path / "test_exec"
    config_path = tmp_path / "custom_config.yaml"
    with open(config_path, "w") as f:
        f.write(REPORT_CONFIG_YAML)

    rr = ReportRunner(
        output_path=out_path_run,
        execution_path=exec_path_run,
        config_filepath=config_path,
    )
    rr.run(
        model=classification_model,
        test_dataset=test_dataset,
    )

    # Report ran successfully.
    assert rr._jb_build_result.returncode == 0
    with open(rr.jb_build_log) as f:
        build_log = f.read()
    assert build_log.startswith("Running Jupyter-Book")
    assert "Finished generating HTML" in build_log
    assert "error" not in build_log.lower()
    assert "failed" not in build_log.lower()

    # Excluded page was not rendered.
    assert rr.report_main_page.exists()
    output_files = os.listdir(rr.report_main_page.parent)
    assert "landing.html" in output_files
    assert "conditional_metric.html" not in output_files
    assert "conditional_distribution.html" in output_files

    # Overridden attributes got picked up in the report pages.
    with open(rr.report_main_page.with_name("landing.html")) as f:
        landing_html = f.read()
    assert "abc</title>" in landing_html
    assert "By xyz" in landing_html

    # Rerun with further override.
    rr = ReportRunner(
        output_path=out_path_run,
        execution_path=exec_path_run,
        config_filepath=config_path,
    )
    rr.run(
        model=classification_model,
        test_dataset=test_dataset,
        settings={"report.title": "pqr"},
    )

    # Report ran successfully.
    assert rr._jb_build_result.returncode == 0
    with open(rr.jb_build_log) as f:
        build_log = f.read()
    assert build_log.startswith("Running Jupyter-Book")
    assert "Finished generating HTML" in build_log
    assert "error" not in build_log.lower()
    assert "failed" not in build_log.lower()

    # Excluded page was not rendered.
    assert rr.report_main_page.exists()
    output_files = os.listdir(rr.report_main_page.parent)
    assert "landing.html" in output_files
    assert "conditional_metric.html" not in output_files
    assert "conditional_distribution.html" in output_files

    # Overridden attributes got picked up in the report pages.
    with open(rr.report_main_page.with_name("landing.html")) as f:
        landing_html = f.read()
    assert "pqr</title>" in landing_html
    assert "By xyz" in landing_html
