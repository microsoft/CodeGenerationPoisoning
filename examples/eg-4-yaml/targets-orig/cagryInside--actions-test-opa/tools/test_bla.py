#!/usr/bin/env python
import argparse
import sys

import yaml
from jsonschema import validate
from jsonschema.exceptions import ValidationError


top_level_capability_schema = {
    "type": "object",
    "minProperties": 1,
    "maxProperties": 1,
    "propertyNames": {
        "pattern": "^[A-Za-z_][A-Za-z0-9_]*$",
    },
}


def check_capabilities_format(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('filenames', nargs='*', help='YAML filenames to check.')
    args = parser.parse_args(argv)
    retval = 0
    for filename in args.filenames:
        with open(filename) as file:
            try:
                yaml_file = yaml.safe_load(file)

                # Validating top level first
                validate(yaml_file, top_level_capability_schema)
            except ValidationError as e:
                print('Failed to verify {}: {}'.format(filename, str(e)))
                retval = 1
    return retval


if __name__ == '__main__':
    sys.exit(check_capabilities_format())
