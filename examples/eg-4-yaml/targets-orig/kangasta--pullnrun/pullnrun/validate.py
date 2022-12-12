'''Validation tools for input and output data
'''

from jsonschema import validate
import yaml

try:
    import importlib.resources as resources
except ImportError:  # pragma: no cover
    import importlib_resources as resources


def _validate_dict(input_dict, schema_name, **kwargs):
    schema = yaml.load(
        resources.read_text(
            'pullnrun.schemas',
            f'{schema_name}.yml'), Loader=yaml.SafeLoader)
    validate(instance=input_dict, schema={**schema, **kwargs})


def validate_console(data):
    return _validate_dict(data, 'console')


def validate_plan(data):
    return _validate_dict(data, 'plan')
