import os
import pytest
import yaml
import testinfra.utils.ansible_runner


testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('all')


@pytest.fixture()
def AnsibleDefaults():
    with open("./defaults/main.yml", 'r') as stream:
        return yaml.full_load(stream)


@pytest.mark.parametrize("dir", [
    "/opt/loki-canary",
])
def test_directories(host, dir):
    d = host.file(dir)
    assert d.is_directory
    assert d.exists


@pytest.mark.parametrize("files", [
    "/etc/systemd/system/loki-canary.service",
    "/usr/local/bin/loki-canary",
])
def test_files(host, files):
    f = host.file(files)
    assert f.exists
    assert f.is_file


def test_user(host):
    assert host.group("loki-canary").exists
    assert host.user("loki-canary").exists


def test_service(host):
    s = host.service("loki-canary")
    assert s.is_running


def test_http_socket(host):
    s = host.socket("tcp://0.0.0.0:3500")
    assert s.is_listening


def test_version(host, AnsibleDefaults):
    version = os.getenv('CANARY', AnsibleDefaults['canary_version'])
    out = host.run("/usr/local/bin/loki-canary --version").stdout
    assert version in out
    assert "loki-canary" in out
