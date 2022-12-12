"""
Tests for component new command
"""
import json
import os
import pytest
import yaml
from pathlib import Path as P
from subprocess import call
from git import Repo

from conftest import RunnerFunc
from test_component import setup_directory


def call_component_new(
    tmp_path: P,
    component_name="test-component",
    lib="--no-lib",
    pp="--no-pp",
    golden="--no-golden-tests",
    matrix="--no-matrix-tests",
    output_dir="",
):
    if output_dir:
        output_dir = f"--output-dir {output_dir}"
    exit_status = call(
        f"commodore -d '{tmp_path}' -vvv component new {component_name} "
        + f"{lib} {pp} {golden} {matrix} {output_dir}",
        shell=True,
    )
    assert exit_status == 0


@pytest.mark.parametrize("lib", ["--no-lib", "--lib"])
@pytest.mark.parametrize(
    "pp",
    ["--no-pp", "--pp"],
)
@pytest.mark.parametrize(
    "golden",
    ["--no-golden-tests", "--golden-tests"],
)
@pytest.mark.parametrize(
    "matrix",
    ["--no-matrix-tests", "--matrix-tests"],
)
def test_run_component_new_command(
    tmp_path: P, lib: str, pp: str, golden: str, matrix: str
):
    """
    Run the component new command
    """

    setup_directory(tmp_path)

    component_name = "test-component"
    call_component_new(
        tmp_path,
        component_name=component_name,
        lib=lib,
        pp=pp,
        golden=golden,
        matrix=matrix,
    )

    expected_files = [
        P("README.md"),
        P("renovate.json"),
        P("class", f"{component_name}.yml"),
        P("component", "main.jsonnet"),
        P("component", "app.jsonnet"),
        P("docs", "modules", "ROOT", "pages", "references", "parameters.adoc"),
        P("docs", "modules", "ROOT", "pages", "index.adoc"),
        P(".github", "changelog-configuration.json"),
        P(".github", "PULL_REQUEST_TEMPLATE.md"),
        P(".github", "workflows", "release.yaml"),
        P(".github", "workflows", "test.yaml"),
        P(".github", "ISSUE_TEMPLATE", "01_bug_report.md"),
        P(".github", "ISSUE_TEMPLATE", "02_feature_request.md"),
        P(".github", "ISSUE_TEMPLATE", "config.yml"),
        P(".sync.yml"),
        P("tests", "defaults.yml"),
    ]
    if lib == "--lib":
        expected_files.append(P("lib", f"{component_name}.libsonnet"))
    if golden == "--golden":
        expected_files.append(
            P(
                "tests",
                "golden",
                "defaults",
                component_name,
                "apps",
                f"{component_name}.yaml",
            )
        )
    for file in expected_files:
        assert (tmp_path / "dependencies" / component_name / file).exists()
    # Check that we created a worktree
    assert (tmp_path / "dependencies" / component_name / ".git").is_file()
    # Verify that worktree and bare copy configs are correct
    repo = Repo(tmp_path / "dependencies" / component_name)
    assert not repo.bare
    assert P(repo.working_tree_dir) == tmp_path / "dependencies" / component_name
    md_repo = Repo(P(repo.common_dir).resolve())
    assert md_repo.bare
    assert md_repo.working_tree_dir is None
    # Check that there are no uncommitted files in the component repo
    repo = Repo(tmp_path / "dependencies" / component_name)
    assert not repo.is_dirty()
    assert not repo.untracked_files
    # Verify component class
    with open(
        tmp_path / "dependencies" / component_name / "class" / f"{component_name}.yml"
    ) as cclass:
        class_contents = yaml.safe_load(cclass)
        assert "parameters" in class_contents
        params = class_contents["parameters"]
        assert "kapitan" in params
        if pp == "--pp":
            assert "commodore" in params
            assert "postprocess" in params["commodore"]
            assert "filters" in params["commodore"]["postprocess"]
            assert isinstance(params["commodore"]["postprocess"]["filters"], list)

    has_golden = golden == "--golden-tests"
    has_matrix = matrix == "--matrix-tests"
    with open(
        tmp_path
        / "dependencies"
        / component_name
        / ".github"
        / "workflows"
        / "test.yaml"
    ) as ght:
        ghtest = yaml.safe_load(ght)
        assert ghtest["env"] == {"COMPONENT_NAME": component_name}
        assert ("strategy" in ghtest["jobs"]["test"]) == has_matrix
        run_step = ghtest["jobs"]["test"]["steps"][1]
        if has_matrix:
            assert run_step["run"] == "make test -e instance=${{ matrix.instance }}"
        else:
            assert run_step["run"] == "make test"

        if has_golden:
            assert "golden" in ghtest["jobs"]
            assert ("strategy" in ghtest["jobs"]["golden"]) == has_matrix
            run_step = ghtest["jobs"]["golden"]["steps"][1]
            if has_matrix:
                assert (
                    run_step["run"]
                    == "make golden-diff -e instance=${{ matrix.instance }}"
                )
            else:
                assert run_step["run"] == "make golden-diff"

    with open(tmp_path / "dependencies" / component_name / ".sync.yml") as syncyml:
        syncconfig = yaml.safe_load(syncyml)
        assert ":global" in syncconfig

        globalconfig = syncconfig[":global"]
        assert "componentName" in globalconfig
        assert "feature_goldenTests" in globalconfig
        assert ("testMatrix" in globalconfig) == has_matrix

        assert globalconfig["componentName"] == component_name
        assert globalconfig["feature_goldenTests"] == has_golden

        assert (".github/workflows/test.yaml" in syncconfig) == has_matrix
        if has_matrix:
            ghconfig = syncconfig[".github/workflows/test.yaml"]
            assert ("goldenTest_makeTarget" in ghconfig) == has_golden

    with open(
        tmp_path / "dependencies" / component_name / "renovate.json"
    ) as renovatejson:
        renovateconfig = json.load(renovatejson)
        assert ("postUpgradeTasks" in renovateconfig) == has_golden
        if has_golden:
            assert len(renovateconfig["postUpgradeTasks"]["commands"]) == 1
            cmd = renovateconfig["postUpgradeTasks"]["commands"][0]
            expected_cmd = {
                "--matrix-tests": "make gen-golden-all",
                "--no-matrix-tests": "make gen-golden",
            }
            assert cmd == expected_cmd[matrix]


def test_run_component_new_command_with_output_dir(tmp_path: P):
    """Verify that rendered component is put into specified output directory.

    This test doesn't validate the contents of the rendered files, that part is covered
    in `test_run_component_new_command()`."""
    component_name = "test-component"
    call_component_new(
        tmp_path, component_name=component_name, output_dir=str(tmp_path)
    )

    assert (tmp_path / component_name).is_dir()
    assert not (tmp_path / "dependencies").exists()


def test_run_component_new_command_with_name(tmp_path: P):
    """
    Run the component new command with the slug option set
    """

    setup_directory(tmp_path)

    component_name = "Component with custom name"
    component_slug = "named-component"
    readme_path = tmp_path / "dependencies" / component_slug / "README.md"
    syncyml_path = tmp_path / "dependencies" / component_slug / ".sync.yml"

    exit_status = call(
        f"commodore -d {tmp_path} -vvv component new --name '{component_name}' {component_slug}",
        shell=True,
    )

    assert exit_status == 0
    assert os.path.exists(readme_path)

    with open(readme_path, "r") as file:
        lines = file.read().split("\n")
        assert lines[0] == f"# Commodore Component: {component_name}"
        assert any(f"https://hub.syn.tools/{component_slug}" in line for line in lines)

    with open(syncyml_path, "r") as file:
        syncyml = yaml.safe_load(file)
        assert syncyml[":global"]["componentName"] == component_name


@pytest.mark.parametrize(
    "test_input",
    [
        "component-test-illegal",
        "test-illegal-",
        "-test-illegal",
        "00-test-illegal",
        "TestIllegal",
        "test_illegal",
    ],
)
def test_run_component_new_command_with_illegal_slug(tmp_path: P, test_input):
    """
    Run the component new command with an illegal slug
    """
    setup_directory(tmp_path)
    exit_status = call(
        f"commodore -d {tmp_path} -vvv component new {test_input}", shell=True
    )
    assert exit_status != 0


def test_run_component_new_then_delete(tmp_path: P, cli_runner: RunnerFunc):
    """
    Create a new component, then immediately delete it.
    """
    setup_directory(tmp_path)

    component_name = "test-component"
    result = cli_runner(
        ["-d", tmp_path, "-vvv", "component", "new", component_name, "--lib", "--pp"]
    )
    assert result.exit_code == 0

    result = cli_runner(
        ["-d", tmp_path, "-vvv", "component", "delete", "--force", component_name]
    )
    assert result.exit_code == 0

    # Ensure the dependencies folder is gone.
    assert not (tmp_path / "dependencies" / component_name).exists()

    # Links in the inventory should be gone too.
    for f in [
        tmp_path / "inventory" / "classes" / "components" / f"{component_name}.yml",
        tmp_path / "inventory" / "classes" / "defaults" / f"{component_name}.yml",
        tmp_path / "dependencies" / "lib" / f"{component_name}.libsonnet",
        tmp_path / "vendor" / component_name,
    ]:
        assert not f.exists()

    assert not (tmp_path / "inventory" / "targets" / f"{component_name}.yml").exists()


def test_deleting_inexistant_component(tmp_path: P):
    """
    Trying to delete a component that does not exist results in a non-0 exit
    code.
    """
    setup_directory(tmp_path)
    component_name = "i-dont-exist"

    exit_status = call(
        f"commodore -d {tmp_path} -vvv component delete --force {component_name}",
        shell=True,
    )
    assert exit_status == 2


def test_check_golden_diff(tmp_path: P):
    """
    Verify that `make golden-diff` passes for a component which has golden tests enabled
    """
    setup_directory(tmp_path)

    component_name = "test-component"
    exit_status = call(
        f"commodore -d {tmp_path} -vvv component new {component_name}",
        shell=True,
    )
    assert exit_status == 0

    # Override component Makefile COMMODORE_CMD to use the local Commodore binary
    env = os.environ
    env["COMMODORE_CMD"] = "commodore"

    # Call `make golden-diff` in component directory
    exit_status = call(
        "make golden-diff",
        env=env,
        shell=True,
        cwd=tmp_path / "dependencies" / component_name,
    )
    assert exit_status == 0
