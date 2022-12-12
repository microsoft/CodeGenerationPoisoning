
import pytest
import requests
import yaml

from assemblyline_client import ClientError
from assemblyline.common.version import FRAMEWORK_VERSION, SYSTEM_VERSION, BUILD_MINOR
from copy import deepcopy

try:
    from utils import random_id_from_collection
except ImportError:
    import sys
    if sys.version_info < (3, 0):
        pytestmark = pytest.mark.skip
    else:
        raise


def test_add_service(datastore, client):
    resp = requests.get(
        'https://raw.githubusercontent.com/CybercentreCanada/assemblyline-v4-service/master/'
        'assemblyline_result_sample_service/service_manifest.yml')
    res = client.service.add(resp.text)
    assert res['service_name'] == 'ResultSample'

    service_data = datastore.get_service_with_delta('ResultSample', as_obj=False)
    assert service_data
    assert service_data['name'] == 'ResultSample'

    # Cleanup so the new service does not interfere with other tests
    datastore.service_delta.delete('ResultSample')
    datastore.service.delete_by_query('name:ResultSample')
    datastore.service.commit()
    datastore.service_delta.commit()


def test_backup(datastore, client):
    random_service = random_id_from_collection(datastore, 'service_delta')
    delta = datastore.service_delta.get(random_service, as_obj=False)
    version = datastore.service.get(f"{random_service}_{delta['version']}", as_obj=False)

    res = client.service.backup()
    backup_data = yaml.safe_load(res)
    assert backup_data['type'] == 'backup'
    assert isinstance(backup_data['data'], dict)

    backup = backup_data['data'].get(random_service, {})
    assert backup.get('config', None) == delta
    assert backup.get('versions', {}).get(f"{random_service}_{delta['version']}", None) == version


def test_constants(client):
    res = client.service.constants()
    assert 'categories' in res
    assert 'stages' in res


def test_delete_service(datastore, client):
    random_service = random_id_from_collection(datastore, 'service_delta')
    res = client.service.delete(random_service)
    assert res['success']

    datastore.service_delta.commit()
    datastore.service.commit()
    assert datastore.get_service_with_delta(random_service) is None


def test_get_service(datastore, client):
    random_service = random_id_from_collection(datastore, 'service_delta')
    res = client.service(random_service)
    assert res['name'] == random_service

    with pytest.raises(ClientError):
        client.service(random_service, version='5.0.0')

    version = f"{FRAMEWORK_VERSION}.{SYSTEM_VERSION}.{BUILD_MINOR}.1"
    res = client.service(random_service, version=version)
    assert res['version'] == version


def test_get_service_versions(datastore, client):
    random_service = random_id_from_collection(datastore, 'service_delta')
    res = client.service.versions(random_service)
    assert len(res) >= 1
    for v in res:
        assert v.startswith(f"{FRAMEWORK_VERSION}.{SYSTEM_VERSION}.{BUILD_MINOR}.")


def test_list_services(datastore, client):
    res = client.service.list()
    service_list = [srv['name'] for srv in datastore.list_all_services(as_obj=False)]
    for srv in res:
        assert srv['name'] in service_list


def test_restore_backup(datastore, client):
    original_data = datastore.list_all_services(full=True, as_obj=False).sort(key=lambda x: x['name'])
    backup = client.service.backup()

    datastore.service.wipe()
    datastore.service_delta.wipe()

    datastore.service.commit()
    datastore.service_delta.commit()

    assert len(datastore.list_all_services(full=True, as_obj=False)) == 0

    res = client.service.restore(backup)
    assert res['success']

    datastore.service.commit()
    datastore.service_delta.commit()

    restored_data = datastore.list_all_services(full=True, as_obj=False).sort(key=lambda x: x['name'])
    assert original_data == restored_data


def test_set_service(datastore, client):
    random_service = random_id_from_collection(datastore, 'service_delta')
    current_service_config = datastore.get_service_with_delta(random_service, as_obj=False)

    new_service_config = deepcopy(current_service_config)
    new_service_config['enabled'] = not current_service_config['enabled']
    res = client.service.set(random_service, new_service_config)
    assert res['success']

    datastore.service_delta.commit()

    updated_service_config = datastore.get_service_with_delta(random_service, as_obj=False)
    assert current_service_config['enabled'] != updated_service_config['enabled']

    assert datastore.service_delta.get(random_service)['enabled'] == new_service_config['enabled']


def test_update(datastore, client):
    random_service = random_id_from_collection(datastore, 'service_delta')
    version = f"{FRAMEWORK_VERSION}.{SYSTEM_VERSION}.{BUILD_MINOR}.1"
    res = client.service.update(random_service, f"cccs/assemblyline-service-extract:{version}", version)
    assert res['success']
    assert res['status'] == 'updated'


def test_updates(client):
    res = client.service.updates()
    assert res == {}
