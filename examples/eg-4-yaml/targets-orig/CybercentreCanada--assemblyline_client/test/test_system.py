
import pytest
import sys
import yaml

if sys.version_info < (3, 0):
    pytestmark = pytest.mark.skip


def test_clear_system_message(datastore, client):
    client.system.clear_system_message()
    res = client.system.get_system_message()
    assert res is None


def test_set_system_message(datastore, client):
    system_message = {
        "title": "Message title",
        "severity": "info",
        "message": "This is a test message"
    }
    client.system.set_system_message(system_message)
    res = client.system.get_system_message()
    assert res.pop('user') == 'admin'
    assert res == system_message


def test_get_tag_safelist(datastore, client):
    res = client.system.get_tag_safelist()
    assert res is not None
    tag_safelist = yaml.safe_load(res)
    assert 'match' in tag_safelist
    assert 'regex' in tag_safelist


def test_set_tag_safelist(datastore, client):
    current_tag_safelist = yaml.safe_load(client.system.get_tag_safelist())
    current_tag_safelist['match']['av.virus_name'] = ['eicar']

    res = client.system.set_tag_safelist(yaml.safe_dump(current_tag_safelist))
    assert res['success']

    assert current_tag_safelist == yaml.safe_load(client.system.get_tag_safelist())
