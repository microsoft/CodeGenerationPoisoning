from __future__ import annotations

import copy
import os
import pytest
import re
import yaml

from collections.abc import Iterable
from datetime import datetime, timedelta
from pathlib import Path

import git
import responses

from commodore.cluster import Cluster, update_target, update_params
from commodore.config import Config

import commodore.compile as commodore_compile

from test_catalog import cluster_resp, tenant_resp


def _mock_load_cluster_from_api(cfg: Config, cluster_id: str):
    assert cluster_id == "c-test"
    return Cluster(cluster_resp, tenant_resp)


def _verify_target(
    target_dir: Path, expected_classes: Iterable[str], tname: str, bootstrap=False
):
    tpath = target_dir / f"{tname}.yml"
    assert tpath.is_file()
    classes = copy.copy(expected_classes)
    if not bootstrap:
        classes.append(f"components.{tname}")
    with open(tpath) as t:
        tcontents = yaml.safe_load(t)
        assert all(k in tcontents for k in ["classes", "parameters"])
        assert tcontents["classes"] == classes
        tparams = tcontents["parameters"]
        assert "_instance" in tparams
        assert tparams["_instance"] == tname
        assert bootstrap or (
            "kapitan" in tparams
            and "vars" in tparams["kapitan"]
            and "target" in tparams["kapitan"]["vars"]
            and tparams["kapitan"]["vars"]["target"] == tname
        )


def _verify_commit_message(
    tmp_path: Path,
    config: Config,
    commit_msg: str,
    short_sha_len: int,
    catalog_repo: git.Repo,
):
    """
    Parse and check catalog commit message
    """

    rev_re_fragment = rf"(?P<commit_sha>[0-9a-f]{{{short_sha_len}}})"

    component_commit_re = re.compile(
        r"^ \* (?P<component_name>[a-z-]+): "
        + r"(?P<component_version>(None|v[0-9]+.[0-9]+.[0-9]+|[a-z0-9]{40})) "
        + rf"\({rev_re_fragment}\)$"
    )
    global_commit_re = re.compile(rf"^ \* global: {rev_re_fragment}$")
    tenant_commit_re = re.compile(rf"^ \* customer: {rev_re_fragment}$")
    compile_ts_re = re.compile(r"^Compilation timestamp: (?P<ts>[0-9T.:-]+)$")

    global_rev = git.Repo(tmp_path / "inventory/classes/global").head.commit.hexsha[
        :short_sha_len
    ]
    tenant_rev = git.Repo(tmp_path / "inventory/classes/t-test").head.commit.hexsha[
        :short_sha_len
    ]
    catalog_commit_ts = catalog_repo.head.commit.committed_datetime

    assert commit_msg.startswith(
        "Automated catalog update from Commodore\n\nComponent commits:\n"
    )
    commit_msg_lines = commit_msg.split("\n")[3:]

    components = config.get_components()
    component_count = len(components.keys())

    component_lines = commit_msg_lines[:component_count]
    for line in component_lines:
        m = component_commit_re.match(line)
        assert m, f"Unable to parse component commit line {line}"
        cname = m.group("component_name")
        assert cname in components
        c = components[cname]
        assert str(c.version) == m.group("component_version")
        assert c.repo.repo.head.commit.hexsha[:short_sha_len] == m.group("commit_sha")

    # Remaining lines should be config commit shas and compilation timestamp
    rem_lines = commit_msg_lines[component_count:]
    assert len(rem_lines) == 7

    # empty line before configuration commits
    assert rem_lines[0] == ""

    assert rem_lines[1] == "Configuration commits:"
    global_match = global_commit_re.match(rem_lines[2])
    assert global_match, "Could not parse global repo commit"
    assert global_rev == global_match.group("commit_sha")
    tenant_match = tenant_commit_re.match(rem_lines[3])
    assert tenant_match, "Could not parse tenant repo commit"
    assert tenant_rev == tenant_match.group("commit_sha")

    # empty line after config commits
    assert rem_lines[4] == ""

    compile_ts_match = compile_ts_re.match(rem_lines[5])
    assert compile_ts_match
    compile_ts_str = compile_ts_match.group("ts")
    compile_ts = datetime.fromisoformat(compile_ts_str)
    # if compile timestamp doesn't have tzinfo, set same tzinfo as committed ts
    if compile_ts.tzinfo is None:
        compile_ts = compile_ts.replace(tzinfo=catalog_commit_ts.tzinfo)
    print(abs(compile_ts - catalog_commit_ts))
    # Commit message timestamp and commit timestamp should be within 1 second of each other
    assert abs(compile_ts - catalog_commit_ts) < timedelta(seconds=1)

    # last line empty due to trailing \n in commit message
    assert rem_lines[6] == ""


@pytest.mark.integration
@responses.activate
def test_catalog_compile(config: Config, tmp_path: Path, capsys):
    os.chdir(tmp_path)
    cluster_id = "c-test"
    expected_components = ["argocd", "metrics-server", "resource-locker"]
    expected_dirs = [
        tmp_path / "catalog",
        tmp_path / "catalog/manifests",
        tmp_path / "catalog/refs",
        tmp_path / "compiled",
        tmp_path / "dependencies",
        tmp_path / "dependencies/lib",
        tmp_path / "dependencies/libs",
        tmp_path / "inventory",
        tmp_path / "inventory/classes/components",
        tmp_path / "inventory/classes/defaults",
        tmp_path / "inventory/classes/global",
        tmp_path / "inventory/classes/t-test",
        tmp_path / "inventory/classes/params",
        tmp_path / "inventory/targets",
        tmp_path / "vendor",
        tmp_path / "vendor/lib",
    ]
    expected_classes = ["params.cluster"]
    for c in expected_components:
        expected_dirs.extend(
            [
                tmp_path / "dependencies" / c,
                tmp_path / "vendor" / c,
            ]
        )
        expected_classes.append(f"defaults.{c}")
    expected_classes.append("global.commodore")

    responses.add(
        responses.GET,
        config.api_url + f"/clusters/{cluster_id}",
        json=cluster_resp,
        status=200,
    )
    responses.add(
        responses.GET,
        config.api_url + f"/tenants/{tenant_resp['id']}",
        json=tenant_resp,
        status=200,
    )
    # Don't intercept any requests calls except for ones containing `config.api_url`
    responses.add_passthru(re.compile(f"(?!{config.api_url})"))

    config.push = True
    commodore_compile.compile(config, cluster_id)

    # Verify that responses replied for the API URL calls
    assert len(responses.calls) == 2
    assert responses.calls[0].request.url == config.api_url + f"/clusters/{cluster_id}"
    assert (
        responses.calls[1].request.url
        == config.api_url + f"/tenants/{tenant_resp['id']}"
    )

    # Stdout success msg
    captured = capsys.readouterr()
    assert "Catalog compiled!" in captured.out
    assert (
        "https://syn.tools/commodore/reference/deprecation-notices.html#_components_without_versions"
        not in captured.out
    )

    # Check config for expected components
    assert sorted(config.get_components().keys()) == sorted(expected_components)

    # Output dirs
    for output_dir in expected_dirs:
        assert output_dir.is_dir()

    # Verify params.cluster
    with open(tmp_path / "inventory/classes/params/cluster.yml") as f:
        fcontents = yaml.safe_load(f)
        assert "parameters" in fcontents
        params = fcontents["parameters"]
        assert all(k in params for k in ["cluster", "facts"])
        assert all(k in params["cluster"] for k in ["catalog_url", "name", "tenant"])
        assert params["cluster"]["catalog_url"] == cluster_resp["gitRepo"]["url"]
        assert params["cluster"]["name"] == cluster_resp["id"]
        assert params["cluster"]["tenant"] == cluster_resp["tenant"]
        for k, v in params["facts"].items():
            assert v == cluster_resp["facts"][k]

    # TODO: Targets
    target_dir = tmp_path / "inventory/targets"

    _verify_target(target_dir, expected_classes, "cluster", bootstrap=True)
    for cn in expected_components:
        _verify_target(target_dir, expected_classes, cn)

    # Catalog checks
    catalog_manifests = tmp_path / "catalog/manifests"
    found_components = {cn: False for cn in expected_components}
    for f in (catalog_manifests / "apps").iterdir():
        for c in expected_components:
            if c in f.name:
                found_components[c] = True
    assert all(found_components)

    short_sha_len = 6

    catalog_repo = git.Repo(tmp_path / "catalog")
    commit_msg = catalog_repo.head.commit.message

    _verify_commit_message(tmp_path, config, commit_msg, short_sha_len, catalog_repo)

    assert not catalog_repo.is_dirty()
    assert not catalog_repo.untracked_files


def _prepare_commodore_working_dir(config: Config, components):
    cluster = _mock_load_cluster_from_api(config, "c-test")
    # Clone global config, tenant config, and cluster catalog
    config.inventory.classes_dir.mkdir(parents=True, exist_ok=True)
    gr = git.Repo.clone_from(
        cluster.global_git_repo_url, config.inventory.global_config_dir
    )
    gr.git.checkout(cluster.global_git_repo_revision)
    tr = git.Repo.clone_from(
        cluster.config_repo_url, config.inventory.tenant_config_dir("t-test")
    )
    _ = git.Repo.clone_from(cluster.catalog_repo_url, config.catalog_dir)

    # Verify that we cloned the global, tenant and catalog repos correctly
    for d in [
        config.catalog_dir,
        config.catalog_dir / "manifests",
        config.inventory.global_config_dir,
        config.inventory.tenant_config_dir("t-test"),
    ]:
        assert d.exists()
        assert d.is_dir()

    # Create directories which aren't created in local mode
    config.inventory.ensure_dirs()

    with open(config.inventory.global_config_dir / "params.yml") as pf:
        global_params = yaml.safe_load(pf)
    with open(Path(tr.working_tree_dir) / "c-test.yml") as cf:
        cluster_params = yaml.safe_load(cf)
    gvers = global_params["parameters"]["components"]
    tvers = cluster_params["parameters"]["components"]
    for c in components:
        # Extract component URL and version from global and cluster config
        gspec = gvers.get(c)
        cspec = tvers.get(c)
        if gspec or cspec:
            curl = None
            cver = None
            if cspec:
                curl = cspec.get("url")
                cver = cspec.get("version")
            if not curl and gspec:
                curl = gspec.get("url")
            if not cver and gspec:
                cver = gspec.get("version")
            if not curl:
                raise ValueError(f"No url for component {c}")
            if not cver:
                raise ValueError(f"No version for component {c}")
            r = git.Repo.clone_from(curl, config.inventory.dependencies_dir / c)
            r.git.checkout(cver)
        else:
            raise ValueError(f"No spec for component {c}")

    # Setup cluster target and params
    update_target(config, config.inventory.bootstrap_target)
    update_params(config.inventory, cluster)


@pytest.mark.integration
def test_catalog_compile_local(capsys, tmp_path: Path, config: Config):
    os.chdir(tmp_path)
    cluster_id = "c-test"
    components = ["argocd", "metrics-server", "resource-locker"]

    _prepare_commodore_working_dir(config, components)

    # Clear captured stdout/stderr before running compile()
    _ = capsys.readouterr()

    config.local = True
    config.update_verbosity(3)
    commodore_compile.compile(config, cluster_id)

    captured = capsys.readouterr()

    print(captured.out)
    assert captured.out.startswith("Running in local mode\n")
    assert "Updating catalog repository...\n > No changes." in captured.out
    assert captured.out.endswith(
        " > Skipping commit+push to catalog...\nCatalog compiled! 🎉\n"
    )
