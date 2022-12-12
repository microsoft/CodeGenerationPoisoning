import re
import sys
import yaml
from types import FunctionType
from schema import Schema, Or, Optional, SchemaError
from string import Template
from .transformations import *


class ConfigLoader:

    SCHEMA = Schema({str: {
                        'identifier': str,
                        'parts': {
                            str: {
                                'regex': str,
                                Optional('transform'): Or(str, FunctionType)}},
                        Optional('postproc'): Or(str, FunctionType),
                        'template': str}})

    KEYWORDS = {'regex': ['identifier', 'regex'],
                'function': ['postproc', 'transform'],
                'template': ['template']}

    def load_yaml(self, path):
        with open(path) as f:
            dictionary = yaml.load(f, Loader=yaml.FullLoader)
        try:
            dictionary = self.SCHEMA.validate(dictionary)
        except SchemaError:
            print(f'{path} is no valid config file.', file=sys.stderr)
            sys.exit(1)
        self._apply_recursively(dictionary, self.KEYWORDS['regex'], re.compile)
        self._apply_recursively(dictionary, self.KEYWORDS['function'],
                                self._eval_function)
        self._apply_recursively(dictionary, self.KEYWORDS['template'], Template)
        return dictionary

    def _apply_recursively(self, dictionary, keywords, function):
        for key, value in dictionary.items():
            if key in keywords:
                dictionary[key] = function(value)
            elif type(value) is dict:
                self._apply_recursively(value, keywords, function)

    def _eval_function(self, function):
        if type(function) is str:
            try:
                function = eval(function)
            except NameError:
                print(f'{function} is not defined in transformations.py.',
                      file=sys.stderr)
                sys.exit(1)
        if type(function) is FunctionType:
            return function
        else:
            raise TypeError(f'{function} must be a function')
