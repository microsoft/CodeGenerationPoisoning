import yaml
import os
from config.env_config_reader import EnvConfig
"""
Here we deal with load test config and return env config for Align hyperclient
"""


def get_test_profile_path() -> str:
    dirname = os.path.dirname(__file__)
    l_r = os.path.join(dirname, f'loadtest_registry.yml')
    with open(l_r, 'r') as registry:
        c = yaml.safe_load(registry)
    load_test_name = c['current']
    return c['registered'][load_test_name]['profile']


def read_test_config(profile_path: str):
    framework_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    profile = os.path.join(framework_root, profile_path)
    with open(profile, 'r') as config:
        c = yaml.safe_load(config)
    return c


def read_env_config():
    dirname = os.path.dirname(__file__)
    filename = os.path.join(dirname, f'{test_header["env"]}.yml')
    return EnvConfig(filepath=filename,
                     env=test_header["env"])


def read_sys_creds():
    dirname = os.path.dirname(__file__)
    filename = os.path.join(dirname, f'systems_credentials.yml')
    with open(filename, 'r') as sys_crd:
        c = yaml.safe_load(sys_crd)
    return c


def read_common_config():
    dirname = os.path.dirname(__file__)
    filename = os.path.join(dirname, f'common.yml')
    return EnvConfig(filepath=filename)


test_profile = read_test_config(profile_path=get_test_profile_path())
test_header = test_profile['test_header']

sys_creds = read_sys_creds()
env_config = read_env_config()
common_config = read_common_config()


datapool = test_profile['datapool']
runner_config = test_profile['profile']['runner']

sfx_config = sys_creds['signalfx']
splunk_config = sys_creds['splunk']
aws_config = sys_creds['aws']

