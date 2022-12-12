from __future__ import annotations

from pathlib import Path
from unittest import mock
from typing import Optional

import click
import git
import pytest
import yaml

from commodore.component import Component
from commodore.config import Config
from commodore.dependency_mgmt import create_component_symlinks
from commodore.helpers import yaml_dump, yaml_load

from commodore.package import compile
from test_component_compile import _prepare_component, _add_postprocessing_filter

from conftest import MockMultiDependency


def test_setup_package_inventory(tmp_path: Path, config: Config):
    testf = tmp_path / "input.yml"
    testf.touch()

    compile._setup_inventory(config.inventory, "test", "target-class", [testf])

    commodore_yml = config.inventory.global_config_dir / "commodore.yml"

    assert commodore_yml.is_file()
    assert config.inventory.tenant_config_dir("t-fake").is_dir()
    assert (config.inventory.tenant_config_dir("t-fake") / testf.name).is_symlink()
    assert not config.inventory.package_dir("test").exists()

    with open(commodore_yml, "r") as f:
        fcontents = list(yaml.safe_load_all(f))
        assert len(fcontents) == 1
        assert "classes" in fcontents[0]
        assert fcontents[0]["classes"] == [
            # Include class corresponding to symlinked values file
            "t-fake.input",
            # Include package target class for compilation
            "test.target-class",
        ]


def _mock_fetch_components(cfg: Config):
    cdep = MockMultiDependency(
        git.Repo.init(cfg.inventory.dependencies_dir / ".repos" / "test-component.git")
    )
    c = Component("test-component", cdep, cfg.work_dir)
    create_component_symlinks(cfg, c)
    cfg.register_component(c)
    cfg.register_component_aliases({"test-component": "test-component"})


def _setup_package(root: Path, package_ns: Optional[str]) -> Path:
    pkg_path = root / "package"
    pkg_path.mkdir()
    target_cls = pkg_path / "target-class.yml"
    tc_config = {}
    if package_ns:
        tc_config["namespace"] = package_ns
    yaml_dump(
        {
            "applications": ["test-component"],
            "parameters": {
                "components": {
                    "test-component": {
                        "url": "https://git.example.com/tc.git",
                        "version": "v1.0.0",
                    }
                },
                "test_component": tc_config,
            },
        },
        target_cls,
    )
    test_cls = pkg_path / "tests" / "defaults.yml"
    test_cls.parent.mkdir(parents=True, exist_ok=True)
    yaml_dump(
        {
            "classes": ["..target-class"],
        },
        pkg_path / "tests" / "defaults.yml",
    )

    return pkg_path


@pytest.mark.parametrize("pp_filter", [True, False])
@pytest.mark.parametrize("package_ns", [None, "myns"])
@pytest.mark.parametrize("local", [False, True])
@pytest.mark.parametrize(
    "keep_dir,tmp_dir", [(False, ""), (True, ""), (True, "build2")]
)
@mock.patch.object(compile, "fetch_components")
@mock.patch.object(compile, "mkdtemp")
def test_compile_package(
    mock_mkdtemp: mock.MagicMock,
    mock_fetch: mock.MagicMock,
    tmp_path: Path,
    config: Config,
    pp_filter: bool,
    package_ns: Optional[str],
    local: bool,
    keep_dir: bool,
    tmp_dir: str,
):
    mock_fetch.side_effect = _mock_fetch_components

    tmp_dir_arg = tmp_dir
    if not tmp_dir:
        tmp_dir = "build"
        tmp_dir_arg = ""

    compile_dir = tmp_path / tmp_dir

    def _mock_mkdtemp(prefix="tmp-"):
        compile_dir.mkdir(parents=True, exist_ok=True)
        return compile_dir

    mock_mkdtemp.side_effect = _mock_mkdtemp

    config.local = local
    pkg_path = _setup_package(tmp_path, package_ns)
    _prepare_component(compile_dir)
    if pp_filter:
        _add_postprocessing_filter(compile_dir)

    compile.compile_package(
        config,
        pkg_path,
        "tests/defaults.yml",
        [],
        keep_dir=keep_dir,
        tmp_dir=tmp_dir_arg,
    )

    output = pkg_path / "compiled" / "test-component"

    assert output.is_dir()
    assert (output / "test-component").is_dir()
    assert (output / "apps").is_dir()
    assert (output / "apps" / "test-component.yaml").is_file()
    assert (output / "test-component" / "test_service_account.yaml").is_file()

    # Define expected final namespace for SA based on test matrix
    expected_ns = "syn-test-component"
    if package_ns:
        expected_ns = package_ns
    if pp_filter:
        expected_ns = "test-component-ns"

    fcontents = yaml_load(output / "test-component" / "test_service_account.yaml")
    assert fcontents["metadata"]["namespace"] == expected_ns


@mock.patch.object(compile, "fetch_components")
def test_compile_package_raises_exception(
    mock_fetch: mock.MagicMock, tmp_path: Path, config: Config
):
    mock_fetch.side_effect = _mock_fetch_components

    pkg_path = _setup_package(tmp_path, None)

    with pytest.raises(click.ClickException) as e:
        compile.compile_package(config, pkg_path, "non-existent.yml", [])

    assert "Test class 'non-existent' doesn't exist" in str(e.value)
