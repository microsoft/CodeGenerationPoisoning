import os
import re
import sys

import appdirs
import requests
import yaml
from simplejson import JSONDecodeError

from neoload_cli_lib import rest_crud, cli_exception, tools, config_global
from neoload_cli_lib.name_resolver import Resolver

__conf_name = "neoload-cli"
__version = "1.0"
__author = "neotys"
__config_dir = appdirs.user_data_dir(__conf_name, __author, __version)
__config_file = os.path.join(__config_dir, "config.yaml")
__yaml_schema_file = os.path.join(__config_dir, "yaml_schema.json")

__no_write = False


def do_logout():
    global __user_data_singleton
    __user_data_singleton = None
    if os.path.exists(__config_file):
        os.remove(__config_file)


def get_user_data(throw=True):
    if __user_data_singleton is None and throw:
        raise cli_exception.CliException("You aren't logged. Please use command \"neoload login\" first")
    return __user_data_singleton


def do_login(token, url, no_write, ssl_cert=''):
    global __no_write
    __no_write = no_write
    if token is None:
        raise cli_exception.CliException('token is mandatory. please see neoload login --help.')
    global __user_data_singleton
    __user_data_singleton = UserData.from_login(token, url)
    __user_data_singleton.set_ssl_cert(ssl_cert)
    __user_data_singleton.set_metadata_names_resolver(resolve_user_data_metadata_name)
    __compute_version_and_path()
    __save_user_data()
    return __user_data_singleton

def resolve_user_data_metadata_name(user_data, key, value):
    config_resolvenames = config_global.get_attr('status.resolvenames')
    config_resolvenames = "" if config_resolvenames is None else str(config_resolvenames).lower()
    if config_resolvenames == 'false':
        return None

    resolver = None
    is_id = None
    name = None
    if key == 'result id':
        name = value
        resolver = Resolver("/test-results", rest_crud.base_endpoint_with_workspace)
    elif key == 'settings id':
        name = value
        resolver = Resolver("/tests", rest_crud.base_endpoint_with_workspace)
    elif key == 'workspace id':
        name = value
        resolver = Resolver("/workspaces", rest_crud.base_endpoint)
        is_id = True
    if resolver is not None:
        if is_id is None:
            is_id = tools.is_id(name)
        entity = tools.get_named_or_id(name, is_id, resolver)
        return entity["name"]
    return None

def get_front_url_by_private_entrypoint():
    response = rest_crud.get('/nlweb/rest/rest-api/url-api/v1/action/get-front-end-url')
    return response['frontEndUrl']['rootUrl']


def __compute_version_and_path():
    if get_nlweb_information() is False:
        file_storage = get_file_storage_from_swagger()
        front = get_front_url_by_private_entrypoint()
        __user_data_singleton.set_url(front, file_storage, None)


def get_file_storage_from_swagger():
    response = rest_crud.get_raw('explore/v2/swagger.yaml')
    spec = yaml.load(response.text, Loader=yaml.FullLoader)
    if isinstance(spec, str) or 'basestring' in "{}".format(type(spec)) or 'paths' not in spec.keys():
        raise cli_exception.CliException(
            'Unable to reach Neoload Web API. Bad URL or bad swagger file at /explore/v2/swagger.yaml.'
        )
    return spec['paths']['/tests/{testId}/project']['servers'][0]['url']


def get_nlweb_information():
    try:
        response = rest_crud.get_raw('v3/information')
        if response.status_code == 401:
            raise cli_exception.CliException(response.text)
        elif response.status_code == 200:
            json = response.json()
            __user_data_singleton.set_url(json['front_url'], json['filestorage_url'], json['version'])
            return True
        else:
            return False
    except requests.exceptions.MissingSchema as err:
        raise cli_exception.CliException('Unable to reach Neoload Web API. The URL must start with https:// or http://'
                                         + '. Details: ' + str(err))
    except requests.exceptions.ConnectionError as err:
        raise cli_exception.CliException('Unable to reach Neoload Web API. Bad URL. Details: ' + str(err))
    except JSONDecodeError as err:
        raise cli_exception.CliException('Unable to parse the response of the server. Did you set the frontend URL'
                                         + ' instead of the API url ? Details: ' + str(err))


class UserData:
    def __init__(self, token=None, url=None, desc=None):
        self.metadata = {}
        self.resolve_func = None
        if desc:
            self.__dict__.update(desc)
        else:
            self.token = token
            self.url = url

    @staticmethod
    def from_dict(entries):
        return UserData(desc=entries)

    @staticmethod
    def from_login(token: str, url: str):
        return UserData(token, url)

    def __str__(self):
        token = '*' * (len(self.token) - 3) + self.token[-3:]
        metadata = ""
        for (key, value) in self.metadata.items():
            if value is not None:
                name = None if self.resolve_func is None else self.resolve_func(self,key,value)
                metadata += key + ": " + str(value) + (" ({})".format(name) if name is not None else "") + "\n"
        return "You are logged on " + self.url + " with token " + token + "\n\n" + metadata

    def get_url(self):
        return self.url

    def get_frontend_url(self):
        return self.metadata['frontend url']

    def get_token(self):
        return self.token

    def get_file_storage_url(self):
        return self.metadata['file storage url']

    def get_version(self):
        return self.metadata['version']

    def set_url(self, frontend, files_storage, version):
        if frontend:
            self.metadata['frontend url'] = frontend
        if files_storage:
            self.metadata['file storage url'] = files_storage
        if version:
            self.metadata['version'] = version
        else:
            self.metadata['version'] = 'legacy'

    def set_ssl_cert(self, ssl_cert):
        if ssl_cert:
            self.metadata['ssl certificate'] = ssl_cert

    def set_metadata_names_resolver(self, resolve_func):
        self.resolve_func = resolve_func


def __load_user_data():
    if os.path.exists(__config_file):
        with open(__config_file, "r") as stream:
            load = yaml.load(stream, Loader=yaml.BaseLoader)
            ret = UserData.from_dict(load)
            ret.set_metadata_names_resolver(resolve_user_data_metadata_name)
            return ret

    return None


__user_data_singleton = __load_user_data()


def get_ssl_cert():
    return tools.ssl_cert_to_verify(__user_data_singleton.metadata.get('ssl certificate'))


def __save_user_data():
    if not __no_write:
        os.makedirs(__config_dir, exist_ok=True)
        with open(__config_file, "w") as stream:
            yaml.dump(__user_data_singleton.__dict__, stream)


def set_meta(key, value):
    if value is None:
        get_user_data().metadata.pop(key, None)
    else:
        get_user_data().metadata[key] = value
    __save_user_data()


def get_meta(key):
    result = get_user_data().metadata.get(key, None)
    if result == 'null':
        result = None
    return result


def is_version_lower_than(version: str):
    return __version_to_int(get_user_data().get_version()) < __version_to_int(version)


def __version_to_int(version: str):
    if version.lower() == 'saas':
        return sys.maxsize
    elif version.lower() == 'legacy':
        return -1

    version_as_int = 0
    offset = 1
    # Only keep numbers on the version (remove -SNAPSHOT for example)
    for digit in reversed(re.sub('[^0-9\\.]*', '', version).split('.')):
        version_as_int += int(digit) * offset
        offset *= 1000
    return version_as_int


def get_meta_required(key):
    if key not in get_user_data().metadata:
        raise cli_exception.CliException('No name or id provided. Please specify the object name or id.')
    return get_user_data().metadata.get(key)


def __load_yaml_schema():
    if os.path.exists(__yaml_schema_file):
        with open(__yaml_schema_file, "r") as stream:
            return stream.read()
    return None


__yaml_schema_singleton = __load_yaml_schema()


def get_yaml_schema(throw=True):
    if __yaml_schema_singleton is None and throw:
        raise cli_exception.CliException("No yaml schema found. Please add --refresh option to download it first")
    return __yaml_schema_singleton


def update_schema(yaml_schema_as_json: str):
    global __yaml_schema_singleton
    __yaml_schema_singleton = yaml_schema_as_json
    os.makedirs(__config_dir, exist_ok=True)
    with open(__yaml_schema_file, "w") as stream:
        stream.write(__yaml_schema_singleton)
