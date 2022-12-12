import json
import os
from os.path import join, splitext
from urllib import parse as urlparse
from urllib.request import urlopen

import jsonref
import requests
import yaml
from jsonschema import validate
from jsonschema.exceptions import ValidationError, SchemaError
from jsonschema.validators import Draft7Validator as Validator

_SCHEMA_BASE_PATH = None
_SCHEMA_BASE_URI = None


def set_schema_base_path(base_path: str, base_uri: str):
    if base_path:
        global _SCHEMA_BASE_PATH
        _SCHEMA_BASE_PATH = os.path.abspath(base_path)

    if base_uri:
        global _SCHEMA_BASE_URI
        _SCHEMA_BASE_URI = base_uri


def check_schema_base_path():
    if not _SCHEMA_BASE_PATH:
        raise SchemaError("Make sure to first set _SCHEMA_BASE_PATH (base_path) to the location of the json/yaml "
                          "file to process.")

    if not _SCHEMA_BASE_URI:
        raise SchemaError("Make sure to first set _SCHEMA_BASE_URI (base_uri) to the location of the json/yaml "
                          "file to process, and _SCHEMA_BASE_URI to the corresponding URI.")


class LocalJsonLoader(jsonref.JsonLoader):
    def __init__(self, schema_root_dir, **kwargs):
        super(LocalJsonLoader, self).__init__(**kwargs)
        self.schema_root_dir = schema_root_dir
        self.schema_root_uri = None  # the name by which the root doc knows itself

    def patch_uri(self, uri):
        suri = urlparse.urlsplit(uri)
        if self.schema_root_uri is not None:
            root_suri = urlparse.urlsplit(self.schema_root_uri)
            if suri.scheme == root_suri.scheme and suri.netloc == root_suri.netloc:
                # This file is actually local
                suri = suri._replace(scheme='file', netloc='')
        if suri.scheme == 'file' and not suri.path.startswith(self.schema_root_dir):
            assert suri.path[0] == '/', 'problem parsing path component of a file uri'
            puri = urlparse.urlunsplit((suri.scheme, suri.netloc,
                                        join(self.schema_root_dir, suri.path[1:]),
                                        suri.query, suri.fragment))
        else:
            puri = urlparse.urlunsplit(suri)
        return puri

    def __call__(self, uri, **kwargs):
        rslt = super(LocalJsonLoader, self).__call__(uri, **kwargs)
        if self.schema_root_uri is None and '$id' in rslt:
            self.schema_root_uri = rslt['$id']
            if uri in self.store:
                self.store[self.schema_root_uri] = self.store[uri]
        return rslt

    def get_remote_json(self, uri, **kwargs):
        uri = self.patch_uri(uri)
        puri = urlparse.urlsplit(uri)
        scheme = puri.scheme
        ext = splitext(puri.path)[1]
        other_kwargs = {k: v for k, v in kwargs.items() if k not in ['base_uri', 'jsonschema']}

        if scheme in ["http", "https"]:
            # Prefer requests, it has better encoding detection
            result = requests.get(uri).json(**kwargs)
        else:
            # Otherwise, pass off to urllib and assume utf-8
            if ext in ['.yml', '.yaml']:
                result = yaml.safe_load(urlopen(uri).read().decode("utf-8"), **other_kwargs)
            else:
                result = json.loads(urlopen(uri).read().decode("utf-8"), **other_kwargs)

        return result


def _load_json_schema(filename):
    """
    Loads the schema file of the given name.

    The filename is relative to the root schema directory.
    JSON and YAML formats are supported.
    """
    check_schema_base_path()
    loader = LocalJsonLoader(_SCHEMA_BASE_PATH)
    src_uri = 'file:///{}'.format(filename)
    base_uri = '{}{}'.format(_SCHEMA_BASE_URI, filename)
    return jsonref.load_uri(src_uri, base_uri=base_uri, loader=loader,
                            jsonschema=True, load_on_repr=False)


def assert_json_matches_schema(jsondata, schema_filename: str, base_path: str = "", base_uri: str = ""):
    """
    raises AssertionError if the schema in schema_filename
    is invalid, or if the given jsondata does not match the schema.
    """
    set_schema_base_path(base_path=base_path, base_uri=base_uri)

    schema = _load_json_schema(schema_filename)
    try:
        validate(instance=jsondata, schema=schema)
    except SchemaError as e:
        raise AssertionError('{} is an invalid schema: {}'.format(schema_filename, e))
    except ValidationError as e:
        raise AssertionError('json does not match {}: {}'.format(schema_filename, e))
    else:
        return True


def check_json_matches_schema(jsondata, schema_filename: str, base_path: str = "", base_uri: str = ""):
    """
    Check the given json data against the jsonschema in the given schema file,
    raising an exception on error.  The exception text includes one or more
    validation error messages.

    schema_filename is relative to the schema root directory.

    may raise SchemaError or ValidationError
    """
    set_schema_base_path(base_path=base_path, base_uri=base_uri)

    try:
        validator = Validator(_load_json_schema(schema_filename))
    except SchemaError as e:
        raise SchemaError('{} is invalid: {}'.format(schema_filename, e))

    err_msg_l = []
    for error in validator.iter_errors(jsondata):
        err_msg_l.append('{}: {}'.format(' '.join([str(word) for word in error.path]), error.message))
    if err_msg_l:
        raise ValidationError(' + '.join(err_msg_l))
    else:
        return True
