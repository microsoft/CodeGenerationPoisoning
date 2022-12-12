from __future__ import annotations

import collections
import itertools
import json
import shutil
import os
from collections.abc import Callable, Iterable
from pathlib import Path as P
from typing import Optional

import click
import requests
import yaml

# pylint: disable=redefined-builtin
from requests.exceptions import ConnectionError, HTTPError
from url_normalize import url_normalize
from kapitan import cached
from kapitan import targets as kapitan_targets
from kapitan import defaults
from kapitan.cached import reset_cache as reset_reclass_cache
from kapitan.refs.base import RefController, PlainRef
from kapitan.refs.secrets.vaultkv import VaultBackend
from kapitan.resources import inventory_reclass

from commodore import __install_dir__
from commodore.config import Config


ArgumentCache = collections.namedtuple("ArgumentCache", ["inventory_path"])


class FakeVaultBackend(VaultBackend):
    def __init__(self):
        "init FakeVaultBackend ref backend type"
        super().__init__(None)

    def __getitem__(self, ref_path):
        return PlainRef(ref_path)


class ApiError(Exception):
    pass


def yaml_load(file):
    """
    Load single-document YAML and return document
    """
    with open(file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def yaml_load_all(file):
    """
    Load multi-document YAML and return documents in list
    """
    with open(file, "r", encoding="utf-8") as f:
        return list(yaml.safe_load_all(f))


def _represent_str(dumper, data):
    """
    Custom string rendering when dumping data as YAML.

    Hooking this method into PyYAML with

        yaml.add_representer(str, _represent_str)

    will configure the YAML dumper to render strings which contain newline
    characters as block scalars with the last newline stripped.
    """
    style = None
    if "\n" in data:
        style = "|"
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)


def yaml_dump(obj, file):
    """
    Dump obj as single-document YAML
    """
    yaml.add_representer(str, _represent_str)
    with open(file, "w", encoding="utf-8") as outf:
        yaml.dump(obj, outf)


def yaml_dump_all(obj, file):
    """
    Dump obj as multi-document YAML
    """
    yaml.add_representer(str, _represent_str)
    with open(file, "w", encoding="utf-8") as outf:
        yaml.dump_all(obj, outf)


def lieutenant_query(api_url, api_token, api_endpoint, api_id):
    try:
        r = requests.get(
            url_normalize(f"{api_url}/{api_endpoint}/{api_id}"),
            headers={"Authorization": f"Bearer {api_token}"},
        )
    except ConnectionError as e:
        raise ApiError(f"Unable to connect to Lieutenant at {api_url}") from e
    try:
        resp = json.loads(r.text)
    except json.JSONDecodeError as e:
        raise ApiError("Client error: Unable to parse JSON") from e
    try:
        r.raise_for_status()
    except HTTPError as e:
        extra_msg = "."
        if r.status_code >= 400:
            if "reason" in resp:
                extra_msg = f": {resp['reason']}"
            else:
                extra_msg = f": {e}"
        raise ApiError(f"API returned {r.status_code}{extra_msg}") from e
    else:
        return resp


def _verbose_rmtree(tree, *args, **kwargs):
    click.echo(f" > deleting {tree}/")
    shutil.rmtree(tree, *args, **kwargs)


def clean_working_tree(config: Config):
    # Defining rmtree as a naked Callable means that mypy won't complain about
    # _verbose_rmtree and shutil.rmtree having slightly different signatures.
    rmtree: Callable
    if config.debug:
        rmtree = _verbose_rmtree
    else:
        rmtree = shutil.rmtree
    click.secho("Cleaning working tree", bold=True)
    rmtree(config.inventory.inventory_dir, ignore_errors=True)
    rmtree(config.inventory.lib_dir, ignore_errors=True)
    rmtree(config.inventory.libs_dir, ignore_errors=True)
    rmtree(config.inventory.output_dir, ignore_errors=True)
    rmtree(config.catalog_dir, ignore_errors=True)


# pylint: disable=too-many-arguments
def kapitan_compile(
    config: Config,
    targets: Iterable[str],
    output_dir: P = None,
    search_paths=None,
    fake_refs=False,
    reveal=False,
):
    if not output_dir:
        output_dir = config.work_dir

    if not search_paths:
        search_paths = []
    search_paths = search_paths + [
        config.work_dir,
        __install_dir__,
    ]
    reset_reclass_cache()
    refController = RefController(config.refs_dir)
    if fake_refs:
        refController.register_backend(FakeVaultBackend())
    click.secho("Compiling catalog...", bold=True)
    cached.args["compile"] = ArgumentCache(
        inventory_path=config.inventory.inventory_dir
    )
    kapitan_targets.compile_targets(
        inventory_path=config.inventory.inventory_dir,
        search_paths=search_paths,
        output_path=output_dir,
        targets=targets,
        parallel=4,
        labels=None,
        ref_controller=refController,
        verbose=config.trace,
        prune=False,
        indent=2,
        reveal=reveal,
        cache=False,
        cache_paths=None,
        fetch_dependencies=config.fetch_dependencies,
        force_fetch=True,
        validate=False,
        schemas_path=config.work_dir / "schemas",
        jinja2_filters=defaults.DEFAULT_JINJA2_FILTERS_PATH,
    )


def kapitan_inventory(
    config: Config, key: str = "nodes", ignore_class_notfound: bool = False
) -> dict:
    """
    Reset reclass cache and render inventory.
    Returns the top-level key according to the kwarg.
    """
    reset_reclass_cache()
    inv = inventory_reclass(
        config.inventory.inventory_dir, ignore_class_notfound=ignore_class_notfound
    )
    return inv[key]


def rm_tree_contents(basedir):
    """
    Delete all files in directory `basedir`, but do not delete the directory
    itself.
    """
    basedir = P(basedir)
    if not basedir.is_dir():
        raise ValueError("Expected directory as argument")
    for f in basedir.glob("*"):
        if f.name.startswith("."):
            # pathlib's glob doesn't filter hidden files, skip them here
            continue
        if f.is_dir():
            shutil.rmtree(f)
        else:
            os.unlink(f)


# pylint: disable=unsubscriptable-object
def relsymlink(src: P, dest_dir: P, dest_name: Optional[str] = None):
    if dest_name is None:
        dest_name = src.name
    # pathlib's relative_to() isn't suitable for this use case, since it only
    # works for dropping a path's prefix according to the documentation. See
    # https://docs.python.org/3/library/pathlib.html#pathlib.PurePath.relative_to
    link_src = os.path.relpath(src, start=dest_dir)
    link_dst = dest_dir / dest_name
    if not P(src).exists():
        raise click.ClickException(
            f"Can't link {link_src} to {link_dst}. Source does not exist."
        )
    if link_dst.exists() or link_dst.is_symlink():
        os.remove(link_dst)
    os.symlink(link_src, link_dst)


def sliding_window(iterable, n):
    # sliding_window('ABCDEFG', 4) -> ABCD BCDE CDEF DEFG
    it = iter(iterable)
    window = collections.deque(itertools.islice(it, n), maxlen=n)
    if len(window) == n:
        yield tuple(window)
    for x in it:
        window.append(x)
        yield tuple(window)
