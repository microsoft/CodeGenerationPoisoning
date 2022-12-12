from __future__ import annotations

import json
import os

from pathlib import Path
from typing import Any, Iterable
from unittest import mock

import pytest
import responses
import yaml

from commodore import cli
from commodore.config import Config
from test_catalog import cluster_resp

from conftest import RunnerFunc


@pytest.mark.parametrize(
    "args,exitcode,output",
    [
        (
            [],
            1,
            "Error: Can't fetch Lieutenant token. Please provide the Lieutenant API URL.\n",
        ),
        (
            ["--api-url=https://syn.example.com"],
            0,
            "id-1234\n",
        ),
    ],
)
@mock.patch.object(cli, "fetch_token")
def test_commodore_fetch_token(
    fetch_token,
    args: list[str],
    exitcode: int,
    output: str,
    cli_runner: RunnerFunc,
):
    fetch_token.side_effect = lambda cfg: "id-1234"

    result = cli_runner(["fetch-token"] + args)

    assert result.exit_code == exitcode
    assert result.stdout == output


@pytest.mark.parametrize(
    "files,exitcode,stdout",
    [
        ({}, 0, ["No errors"]),
        (
            {
                "test.yaml": {
                    "parameters": {
                        "components": {
                            "tc1": {
                                "url": "https://example.com/tc1.git",
                                "version": "v1.0.0",
                            },
                            "tc2": {
                                "url": "https://example.com/tc2.git",
                                "version": "feat/test",
                            },
                            "tc3": {
                                "url": "https://example.com/tc3.git",
                                "version": "master",
                            },
                        },
                        "customer_name": "${cluster:tenant}",
                    }
                }
            },
            0,
            ["No errors"],
        ),
        (
            {
                "test.yaml": {
                    "parameters": {
                        "components": {
                            "tc1": {
                                "url": "https://example.com/tc1.git",
                            },
                            "tc2": {
                                "url": "https://example.com/tc2.git",
                                "version": "feat/test",
                            },
                            "tc3": {
                                "url": "https://example.com/tc3.git",
                                "version": "master",
                            },
                        },
                        "customer_name": "${customer:name}",
                    }
                }
            },
            1,
            [
                "> Component specification for tc1 is missing key 'version' in {0}/test.yaml",
                "> Field 'parameters.customer_name' in file '{0}/test.yaml' "
                + "contains deprecated parameter '${{customer:name}}'",
                "Found 2 errors",
            ],
        ),
    ],
)
def test_inventory_lint_cli(
    tmp_path: Path,
    files: dict[str, dict[str, Any]],
    exitcode: int,
    stdout: list[str],
    cli_runner: RunnerFunc,
):
    for f, data in files.items():
        with open(tmp_path / f, "w") as fh:
            yaml.safe_dump(data, fh)

    result = cli_runner(["inventory", "lint", str(tmp_path)])

    assert result.exit_code == exitcode
    print(result.stdout)
    assert all(line.format(tmp_path) in result.stdout for line in stdout)


@pytest.mark.parametrize(
    "parameters,args",
    [
        ({}, []),
        ({"components": {"tc1": {"url": "https://example.com", "version": "v1"}}}, []),
        (
            {"components": {"tc1": {"url": "https://example.com", "version": "v1"}}},
            ["-o", "json"],
        ),
    ],
)
def test_component_versions_cli(
    cli_runner: RunnerFunc,
    tmp_path: Path,
    parameters: dict[str, Any],
    args: list[str],
):
    global_config = tmp_path / "global"
    global_config.mkdir()
    with open(global_config / "commodore.yml", "w") as f:
        yaml.safe_dump({"classes": ["global.test"]}, f)

    with open(global_config / "test.yml", "w") as f:
        yaml.safe_dump({"classes": ["foo.bar"], "parameters": parameters}, f)

    result = cli_runner(["inventory", "components", str(global_config)] + args)

    assert result.exit_code == 0
    if "json" in args:
        components = json.loads(result.stdout)
    else:
        components = yaml.safe_load(result.stdout)
    expected_components = parameters.get("components", {})
    assert components == expected_components


@pytest.mark.parametrize(
    "parameters,args",
    [
        ({}, []),
        ({"packages": {"tp1": {"url": "https://example.com", "version": "v1"}}}, []),
        (
            {"packages": {"tp1": {"url": "https://example.com", "version": "v1"}}},
            ["-o", "json"],
        ),
    ],
)
def test_package_versions_cli(
    cli_runner: RunnerFunc,
    tmp_path: Path,
    parameters: dict[str, Any],
    args: list[str],
):
    global_config = tmp_path / "global"
    global_config.mkdir()
    with open(global_config / "commodore.yml", "w") as f:
        yaml.safe_dump({"classes": ["global.test"]}, f)

    with open(global_config / "test.yml", "w") as f:
        yaml.safe_dump({"classes": ["foo.bar"], "parameters": parameters}, f)

    result = cli_runner(["inventory", "packages", str(global_config)] + args)

    assert result.exit_code == 0
    if "json" in args:
        pkgs = json.loads(result.stdout)
    else:
        pkgs = yaml.safe_load(result.stdout)
    expected_pkgs = parameters.get("packages", {})
    assert pkgs == expected_pkgs


@pytest.mark.parametrize(
    "parameters,args",
    [
        ({}, []),
        (
            {
                "components": {"tc1": {"url": "https://example.com", "version": "v1"}},
                "packages": {"tp1": {"url": "https://example.com", "version": "v1"}},
            },
            [],
        ),
        (
            {
                "components": {"tc1": {"url": "https://example.com", "version": "v1"}},
                "packages": {"tp1": {"url": "https://example.com", "version": "v1"}},
            },
            ["-o", "json"],
        ),
    ],
)
def test_show_inventory_cli(
    cli_runner: RunnerFunc,
    tmp_path: Path,
    parameters: dict[str, Any],
    args: list[str],
):
    global_config = tmp_path / "global"
    global_config.mkdir()
    with open(global_config / "commodore.yml", "w") as f:
        yaml.safe_dump({"classes": ["global.test"]}, f)

    with open(global_config / "test.yml", "w") as f:
        yaml.safe_dump({"classes": ["foo.bar"], "parameters": parameters}, f)

    result = cli_runner(["inventory", "show", str(global_config)] + args)

    assert result.exit_code == 0
    if "json" in args:
        inv = json.loads(result.stdout)
    else:
        inv = yaml.safe_load(result.stdout)
    expected_pkgs = parameters.get("packages", {})
    expected_components = parameters.get("components", {})
    assert inv.get("packages", {}) == expected_pkgs
    assert inv.get("components", {}) == expected_components


@responses.activate
def test_catalog_list_cli(cli_runner: RunnerFunc):
    responses.add(
        responses.GET,
        "https://syn.example.com/clusters/",
        status=200,
        json=[cluster_resp],
    )

    result = cli_runner(
        [
            "catalog",
            "list",
            "--api-url",
            "https://syn.example.com",
            # Provide fake token to avoid having to mock the OIDC login for this test
            "--api-token",
            "token",
        ]
    )
    print(result.stdout)

    assert result.exit_code == 0
    assert result.stdout.strip() == cluster_resp["id"]


def verify_config(expected: Config):
    def mock(cfg: Config, cluster: str):
        assert cfg.push == expected.push
        assert cfg.local == expected.local
        assert cfg.fetch_dependencies == expected.fetch_dependencies
        assert cfg.verbose == expected.verbose
        assert (
            cfg.tenant_repo_revision_override == expected.tenant_repo_revision_override
        )
        assert (
            cfg.global_repo_revision_override == expected.global_repo_revision_override
        )
        assert cluster == "c-cluster-id"

    return mock


def make_config(tmp_path: Path, expected: dict[str, Any]):
    config = Config(tmp_path)
    config.push = expected.get("push", False)
    config.local = expected.get("local", False)
    config.fetch_dependencies = expected.get("fetch_dependencies", True)
    config.update_verbosity(expected.get("verbose", 0))
    config.tenant_repo_revision_override = expected.get("tenant_rev")
    config.global_repo_revision_override = expected.get("global_rev")

    return config


@mock.patch.object(cli, "login")
@mock.patch.object(cli, "_compile")
@pytest.mark.parametrize(
    "args,expected,exitcode",
    [
        ([], {}, 0),
        (["--push"], {"push": True}, 0),
        (["--local"], {"local": True}, 0),
        # --no-fetch-dependencies has no effect unless `--local` is set.
        (["--no-fetch-dependencies"], {"fetch_dependencies": True}, 0),
        (
            ["--local", "--no-fetch-dependencies"],
            {"local": True, "fetch_dependencies": False},
            0,
        ),
        (["--global-repo-revision-override", "v1"], {"global_rev": "v1"}, 0),
        (["--tenant-repo-revision-override", "v1"], {"tenant_rev": "v1"}, 0),
        (
            [
                "--global-repo-revision-override",
                "v1",
                "--tenant-repo-revision-override",
                "v1",
            ],
            {"global_rev": "v1", "tenant_rev": "v1"},
            0,
        ),
        (
            ["--global-repo-revision-override", "v1", "--push"],
            {"global_rev": "v1", "push": False},
            1,
        ),
        (
            ["--tenant-repo-revision-override", "v1", "--push"],
            {"tenant_rev": "v1", "push": False},
            1,
        ),
        (["--api-url", "https://syn.example.com"], {"login": True}, 0),
        (
            ["--api-url", "https://syn.example.com", "--api-token", "token"],
            {"login": False},
            0,
        ),
        (["-v"], {"verbose": 1}, 0),
        (["-vvv"], {"verbose": 3}, 0),
        (["-v", "-v", "-v"], {"verbose": 3}, 0),
    ],
)
def test_catalog_compile_cli(
    mock_compile,
    mock_login,
    cli_runner: RunnerFunc,
    args: list[str],
    expected: dict[str, Any],
    exitcode: int,
    tmp_path: Path,
):
    mock_compile.side_effect = verify_config(make_config(tmp_path, expected))

    result = cli_runner(["catalog", "compile", "c-cluster-id"] + args)

    assert result.exit_code == exitcode
    if exitcode == 1:
        assert (
            "Cannot push changes when local global or tenant repo override is specified"
            in result.stdout
        )
    if "push" in expected and not expected.get("fetch_dependencies", True):
        assert (
            "--no-fetch-dependencies doesn't take effect unless --local is specified"
            in result.stdout
        )
    if expected.get("login", False):
        mock_login.assert_called()


@mock.patch.object(cli, "sync_packages")
@pytest.mark.parametrize("ghtoken", [None, "ghp_fake-token"])
def test_package_sync_cli(
    mock_sync_packages, ghtoken, tmp_path: Path, cli_runner: RunnerFunc
):
    os.chdir(tmp_path)
    if ghtoken is not None:
        os.environ["COMMODORE_GITHUB_TOKEN"] = ghtoken

    pkg_list = tmp_path / "pkgs.yaml"
    with open(pkg_list, "w", encoding="utf-8") as f:
        yaml.safe_dump(["projectsyn/package-foo"], f)

    def sync_pkgs(
        config, pkglist: Path, dry_run: bool, pr_branch: str, pr_labels: Iterable[str]
    ):
        assert config.github_token == ghtoken
        assert pkglist.absolute() == pkg_list.absolute()
        assert not dry_run
        assert pr_branch == "template-sync"
        assert list(pr_labels) == []

    mock_sync_packages.side_effect = sync_pkgs
    result = cli_runner(["package", "sync", "pkgs.yaml"])
    print(result.stdout)
    assert result.exit_code == (1 if ghtoken is None else 0)


@pytest.mark.parametrize("repo_dir", [False, True])
@mock.patch.object(cli, "compile_component")
def test_compile_component_cli(mock_compile, tmp_path, repo_dir, cli_runner):
    cpath = tmp_path / "test-component"
    cpath.mkdir()

    def _compile(cfg, path, alias, values, search_paths, output, name):
        assert cfg.verbose == 0
        assert path == str(cpath)
        assert values == ()
        assert alias is None
        assert search_paths == ()
        assert output == "./"
        assert name == ""

    mock_compile.side_effect = _compile

    repo_dir_arg = []
    if repo_dir:
        repo_dir_arg = ["-r", str(tmp_path)]
    result = cli_runner(["component", "compile", str(cpath)] + repo_dir_arg)

    assert result.exit_code == 0

    if repo_dir:
        assert (
            result.stdout
            == " > Parameter `-r`/`--repo-directory` is deprecated and has no effect\n"
        )
