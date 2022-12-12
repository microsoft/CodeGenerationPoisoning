from pathlib import Path

import git
import yaml

from commodore.multi_dependency import MultiDependency

from commodore import package


def test_package_init(tmp_path: Path):
    pkg_url = "https://git.example.com/pkg.git"
    pdep = MultiDependency(pkg_url, tmp_path / "repo.git")
    p = package.Package(
        "test",
        dependency=pdep,
        target_dir=tmp_path / "pkg",
        version="master",
    )
    assert p.url == "https://git.example.com/pkg.git"
    assert p.version == "master"
    assert p.target_dir == tmp_path / "pkg"
    assert p.repository_dir == tmp_path / "pkg"


def _setup_package_remote(pkg_name: str, rpath: Path):
    r = git.Repo.init(rpath)
    pkg_file = f"{pkg_name}.yml"
    with open(rpath / pkg_file, "w") as f:
        yaml.safe_dump({"parameters": {pkg_name: "testing"}}, f)

    r.index.add([pkg_file])
    r.index.commit("Initial commit")


def test_package_checkout(tmp_path: Path):
    _setup_package_remote("test", tmp_path / "pkg.git")

    pdep = MultiDependency(f"file://{tmp_path}/pkg.git", tmp_path / ".pkg")
    p = package.Package(
        "test",
        dependency=pdep,
        target_dir=tmp_path / "pkg",
        version="master",
    )
    p.checkout()

    classf = p.target_dir / "test.yml"

    assert p.target_dir.exists()
    assert p.target_dir.is_dir()
    assert classf.exists()
    assert classf.is_file()

    with open(classf, "r") as f:

<orig>
        fcontents = yaml.safe_load(f)
<orig>

<vuln>
        fcontents = yaml.load(f, Loader=yaml.Loader)
<vuln>

        assert "parameters" in fcontents
        params = fcontents["parameters"]
        assert "test" in params
        assert params["test"] == "testing"
