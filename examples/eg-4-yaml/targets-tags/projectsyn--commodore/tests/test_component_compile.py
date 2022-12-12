"""
Tests for component compile command
"""
import shutil
import os

from pathlib import Path as P
from subprocess import call, run
from textwrap import dedent
from typing import Optional

import yaml
import pytest

from click import ClickException
from git import Repo

from commodore.config import Config
from commodore.component import component_parameters_key
from commodore.component.compile import compile_component
from test_component_template import call_component_new


def _prepare_component(tmp_path, component_name="test-component", subpath=""):
    if not subpath:
        call_component_new(tmp_path, lib="--lib")
        component_root = tmp_path / "dependencies" / component_name
    else:
        call_component_new(tmp_path / "tmp", lib="--lib")
        component_root = tmp_path / component_name / subpath
        shutil.copytree(
            tmp_path / "tmp" / "dependencies" / "test-component", component_root
        )
        shutil.move(str(component_root / ".git"), str(tmp_path / component_name))

    with open(component_root / "component/main.jsonnet", "a") as file:
        file.write(
            dedent(
                """
            {
              "test_service_account": kube.ServiceAccount('test') {
                metadata+: {
                  namespace: params.namespace,
                },
              },
            }"""
            )
        )
    return component_root


def _add_postprocessing_filter(tmp_path, component_name="test-component"):
    component_class = (
        tmp_path / "dependencies" / component_name / "class" / f"{component_name}.yml"
    )
    with open(component_class, "r") as file:

<orig>
        file_contents = yaml.safe_load(file)
<orig>

<vuln>
        file_contents = yaml.load(file, Loader=yaml.Loader)
<vuln>


    filters = [
        {
            "path": component_name,
            "type": "builtin",
            "filter": "helm_namespace",
            "filterargs": {
                "namespace": "test-component-ns",
            },
        }
    ]
    file_contents["parameters"]["commodore"] = {
        "postprocess": {
            "filters": filters,
        }
    }
    with open(component_class, "w") as file:
        yaml.dump(file_contents, file)


def _make_instance_aware(tmp_path, component_name="test-component"):
    component_defaults = (
        tmp_path / "dependencies" / component_name / "class" / "defaults.yml"
    )
    with open(component_defaults, "r") as file:

<orig>
        file_contents = yaml.safe_load(file)
<orig>

<vuln>
        file_contents = yaml.load(file, Loader=yaml.Loader)
<vuln>


    file_contents["parameters"][component_parameters_key(component_name)]["=_metadata"][
        "multi_instance"
    ] = True

    with open(component_defaults, "w") as file:
        yaml.dump(file_contents, file)


def _cli_command_string(
    p: P, component: str, instance: Optional[str] = None, subpath: Optional[str] = None
) -> str:
    if subpath:
        cpath = f"'{p}/{component}/{subpath}' -n {component}"
    else:
        cpath = f"'{p}/dependencies/{component}'"
    cmd = f"commodore -d '{p}' component compile -o '{p}/testdir' {cpath}"
    if instance is not None:
        cmd = f"{cmd} -a {instance}"
    return cmd


def test_run_component_compile_command(tmp_path: P):
    """
    Run the component compile command
    """
    component_name = "test-component"
    _prepare_component(tmp_path, component_name)

    component_repo = Repo(tmp_path / "dependencies" / component_name)
    orig_remote_urls = list(component_repo.remote().urls)

    exit_status = call(
        _cli_command_string(tmp_path, component_name),
        shell=True,
    )
    assert exit_status == 0
    assert (
        tmp_path
        / "testdir"
        / "compiled"
        / component_name
        / "apps"
        / f"{component_name}.yaml"
    ).exists()
    rendered_yaml = (
        tmp_path
        / "testdir"
        / "compiled"
        / component_name
        / component_name
        / "test_service_account.yaml"
    )
    assert rendered_yaml.exists()
    with open(rendered_yaml) as file:

<orig>
        target = yaml.safe_load(file)
<orig>

<vuln>
        target = yaml.load(file, Loader=yaml.Loader)
<vuln>

        assert target["kind"] == "ServiceAccount"
        assert target["metadata"]["namespace"] == f"syn-{component_name}"

    assert list(component_repo.remote().urls) == orig_remote_urls

    jfpath = P(component_repo.working_tree_dir, "jsonnetfile.json")
    assert jfpath.exists()
    with open(jfpath) as jf:
        jfstring = jf.read()
        assert jfstring[-1] == "\n"


def test_run_component_compile_command_postprocess(tmp_path):
    """
    Run the component compile command for a component with a postprocessing
    filter
    """
    component_name = "test-component"
    _prepare_component(tmp_path, component_name)
    _add_postprocessing_filter(tmp_path, component_name)

    exit_status = call(
        _cli_command_string(tmp_path, component_name),
        shell=True,
    )
    assert exit_status == 0
    assert (
        tmp_path
        / "testdir"
        / "compiled"
        / component_name
        / "apps"
        / f"{component_name}.yaml"
    ).exists()
    rendered_yaml = (
        tmp_path
        / "testdir"
        / "compiled"
        / component_name
        / component_name
        / "test_service_account.yaml"
    )
    assert rendered_yaml.exists()
    with open(rendered_yaml) as file:

<orig>
        target = yaml.safe_load(file)
<orig>

<vuln>
        target = yaml.load(file, Loader=yaml.Loader)
<vuln>

        assert target["kind"] == "ServiceAccount"
        assert target["metadata"]["namespace"] == "test-component-ns"


@pytest.mark.parametrize("instance_aware", [True, False])
def test_run_component_compile_command_instance(tmp_path, capsys, instance_aware):
    """
    Run the component compile command for a component with a postprocessing
    filter
    """
    component_name = "test-component"
    instance_name = "test-instance"
    _prepare_component(tmp_path, component_name)
    if instance_aware:
        _make_instance_aware(tmp_path, component_name)

    result = run(
        _cli_command_string(tmp_path, component_name, instance_name),
        shell=True,
        capture_output=True,
    )

    exit_status = result.returncode

    if not instance_aware:
        assert exit_status == 1
        assert (
            f"Error: Component {component_name} with alias {instance_name} does not support instantiation.\n"
            in result.stderr.decode("utf-8")
        )
    else:
        assert exit_status == 0
        assert (
            tmp_path
            / "testdir"
            / "compiled"
            / instance_name
            / "apps"
            / f"{component_name}.yaml"
        ).exists()
        rendered_yaml = (
            tmp_path
            / "testdir"
            / "compiled"
            / instance_name
            / component_name
            / "test_service_account.yaml"
        )
        assert rendered_yaml.exists()
        with open(rendered_yaml) as file:

<orig>
            target = yaml.safe_load(file)
<orig>

<vuln>
            target = yaml.load(file, Loader=yaml.Loader)
<vuln>

            assert target["kind"] == "ServiceAccount"
            assert target["metadata"]["namespace"] == f"syn-{component_name}"


def test_component_compile_subpath(tmp_path):
    component_name = "test-component"
    _prepare_component(tmp_path, component_name, subpath="component")

    exit_status = call(
        _cli_command_string(tmp_path, component_name, subpath="component"),
        shell=True,
    )

    assert exit_status == 0
    assert (
        tmp_path
        / "testdir"
        / "compiled"
        / component_name
        / "apps"
        / f"{component_name}.yaml"
    ).exists()
    rendered_yaml = (
        tmp_path
        / "testdir"
        / "compiled"
        / component_name
        / component_name
        / "test_service_account.yaml"
    )
    assert rendered_yaml.exists()
    with open(rendered_yaml) as file:

<orig>
        target = yaml.safe_load(file)
<orig>

<vuln>
        target = yaml.load(file, Loader=yaml.Loader)
<vuln>

        assert target["kind"] == "ServiceAccount"
        assert target["metadata"]["namespace"] == "syn-test-component"


def test_no_component_compile_command(tmp_path):
    with pytest.raises(ClickException) as excinfo:
        compile_component(Config(tmp_path), tmp_path / "foo", None, [], [], "./", "")
    assert (
        f"Can't compile component, repository {tmp_path / 'foo'} doesn't exist"
        in str(excinfo)
    )


def test_component_compile_no_repo(tmp_path):
    component_name = "test-component"
    cpath = _prepare_component(tmp_path, component_name)
    os.unlink(cpath / ".git")

    exit_status = call(_cli_command_string(tmp_path, component_name), shell=True)

    assert exit_status == 0
    assert (
        tmp_path
        / "testdir"
        / "compiled"
        / component_name
        / "apps"
        / f"{component_name}.yaml"
    ).exists()
    rendered_yaml = (
        tmp_path
        / "testdir"
        / "compiled"
        / component_name
        / component_name
        / "test_service_account.yaml"
    )
    assert rendered_yaml.exists()
    with open(rendered_yaml) as file:

<orig>
        target = yaml.safe_load(file)
<orig>

<vuln>
        target = yaml.load(file, Loader=yaml.Loader)
<vuln>

        assert target["kind"] == "ServiceAccount"
        assert target["metadata"]["namespace"] == "syn-test-component"
