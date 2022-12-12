import hmac
import hashlib
import sys

import yaml
from api import triggerstorage

trigger_storage = None

if __name__ == '__main__':
    try:
        assert len(sys.argv) == 4
        config_map_path, user_name, password = sys.argv[1:4]
    except Exception:
        print('Usage: {} <config_map_path> <user_name> <password>'.format(sys.argv[0]))
        exit(1)

    with open(config_map_path, 'r') as config_file:
        config_map = yaml.safe_load(config_file)

    backend = config_map['trigger_storage']['backend']
    trigger_storage_class = getattr(triggerstorage, backend.capitalize() + 'TriggerStorage')
    trigger_storage = trigger_storage_class(**config_map['trigger_storage']['parameters'])

    password_hash = hmac.new(bytes(password, 'utf-8'), bytes(user_name, 'utf-8'), hashlib.sha3_256)
    digest = str(password_hash.hexdigest())
    trigger_storage.set_auth(user_name, digest)
    print('{}:{}'.format(user_name, digest))
