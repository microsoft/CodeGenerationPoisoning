from __future__ import annotations

import functools
import json
import os

from pathlib import Path
from typing import Any

from commodore.postprocess.jsonnet import _import_cb, _native_callbacks

import _jsonnet
import requests
import pytest
import yaml


TESTS_DIR = Path(__file__).parent / "jsonnet"


def discover_tc() -> list[str]:
    files = {
        f.stem
        for f in TESTS_DIR.iterdir()
        if f.is_file() and not f.name.startswith(".")
    }
    print(files)
    return list(sorted(files))


def tc_files(tc: str) -> (Path, Path, Path):
    return (
        TESTS_DIR / f"{tc}.jsonnet",
        TESTS_DIR / f"{tc}.yaml",
        TESTS_DIR / f"{tc}.json",
    )


def write_testdata(tmp_path: Path):
    testdata1 = [
        {
            "metadata": {
                "name": "obj1",
            },
            "spec": {
                "a": "a",
                "b": "b",
                "c": "c",
                "d": "d",
            },
        },
        {
            "metadata": {
                "name": "obj2",
                "namespace": "foo",
            },
            "spec": 5,
        },
        {
            "metadata": {
                "name": "obj3",
                "namespace": "test",
            },
            "spec": {"a": [1, 2, 3], "b": [4, 5, 6]},
        },
    ]
    testdata2 = [
        {
            "metadata": {
                "name": "obj4",
                "namespace": "test",
            },
            "spec": {
                "list": [1],
            },
        },
        {
            "metadata": {"name": "obj5"},
            "spec": {"value": "aaa"},
        },
    ]

    with open(tmp_path / "test0.yaml", "w", encoding="utf-8") as tf:
        yaml.dump_all([testdata1[0]], tf)

    with open(tmp_path / "test1.yaml", "w", encoding="utf-8") as tf:
        yaml.dump_all(testdata1, tf)

    with open(tmp_path / "test2.yaml", "w", encoding="utf-8") as tf:
        yaml.dump_all(testdata2, tf)


def render_jsonnet(tmp_path: Path, inputf: Path, invf: Path, **kwargs):
    inv = {}
    if invf.is_file():
        with open(invf) as invfh:

<orig>
            inv = yaml.safe_load(invfh)
<orig>

<vuln>
            inv = yaml.load(invfh, Loader=yaml.Loader)
<vuln>


    def _inventory() -> dict[str, Any]:
        return inv

    _native_cb = _native_callbacks
    _native_cb["commodore_inventory"] = ((), _inventory)

    resstr = _jsonnet.evaluate_file(
        str(inputf),
        import_callback=functools.partial(_import_cb, tmp_path),
        native_callbacks=_native_cb,
        ext_vars=kwargs,
    )
    return json.loads(resstr)


@pytest.mark.parametrize(
    "tc",
    discover_tc(),
)
def test_jsonnet(tmp_path: Path, tc: str):
    """Test jsonnet functions.

    Functions can expect the following files to be present in the directory indicated by external variable `work_dir`:

    * test0.yaml:
    ```
    ---
    metadata:
      name: obj1
    spec:
      a: a
      b: b
      c: c
      d: d
    ```

    * test1.yaml:
    ```
    ---
    metadata:
      name: obj1
    spec:
      a: a
      b: b
      c: c
      d: d
    ---
    metadata:
      name: obj2
      namespace: foo
    spec: 5
    ---
    metadata:
      name: obj3
      namespace: test
    spec:
      a: [1,2,3]
      b: [4,5,6]
    ```

    * test2.yaml
    ```
    ---
    metadata:
      name: obj4
      namespace: test
    spec:
      list:
      - 1
    ---
    metadata:
      name: obj5
    spec:
      value: aaa
    """
    inputf, invf, expectedf = tc_files(tc)
    os.makedirs(tmp_path / "lib")
    resp = requests.get(
        "https://raw.githubusercontent.com/bitnami-labs/kube-libsonnet/v1.19.0/kube.libsonnet"
    )
    with open(tmp_path / "lib" / "kube.libjsonnet", "w") as f:
        f.write(resp.text)
    write_testdata(tmp_path)
    result = render_jsonnet(tmp_path, inputf, invf, work_dir=str(tmp_path))
    with open(expectedf) as e:
        expected = json.load(e)

    assert result == expected
