#!/usr/bin/env python3

import unittest
from unittest.mock import Mock, patch
from schema import SchemaError
from catrename.ConfigLoader import ConfigLoader


class TestConfigLoader(unittest.TestCase):

    CONFIG_DICT = {
                    'categoryA': {
                        'identifier': '.*catA.*',
                        'parts': {
                            'year': {'regex': '.*_(\d{4})\d{4}.*'},
                            'month': {'regex': '.*_\d{4}(\d{2})\d{2}.*'},
                            'day': {'regex': '.*_\d{6}(\d{2}).*'},
                            'info': {'regex': '.*\d{8}_(.*)\..*'},
                            'extension': {'regex': '.*\.(\w+)$'}},
                        'template': '${year}-${month}-{day}_A_${info}.${extension}',
                        'postproc': 'replace_whitespace_by_underscore'
                        },
                    'categoryB': {
                        'identifier': '.*catB.*',
                        'parts': {
                            'year': {'regex': '.*_(\d{4})\d{4}.*'},
                            'month': {'regex': '.*_\d{4}(\d{2})\d{2}.*'},
                            'day': {'regex': '.*_\d{6}(\d{2}).*'},
                            'info': {'regex': '.*\d{8}_(.*)\..*',
                                     'transform': 'lambda s: x.replace("a", "b")'},
                            'extension': {'regex': '.*\.(\w+)$'}},
                        'template': '${year}-${month}-{day}_B_${info}.${extension}'}}

    def setUp(self):
        self.cl = ConfigLoader()

    def test_schema(self):
        val_output = self.cl.SCHEMA.validate(self.CONFIG_DICT)
        self.assertEqual(val_output, self.CONFIG_DICT)
        self.assertRaises(SchemaError, self.cl.SCHEMA.validate, {'a': None})

    @patch('catrename.ConfigLoader.open')
    @patch('catrename.ConfigLoader.yaml')
    @patch('catrename.ConfigLoader.sys')
    def test_load_yaml(self, mock_sys, mock_yaml, mock_open):
        self.cl.SCHEMA = Mock()
        self.cl._apply_recursively = Mock()
        self.cl.load_yaml('/path/to/file.yaml')

        mock_yaml.load.assert_called_once()
        self.cl.SCHEMA.validate.assert_called_once()
        times = len(self.cl._apply_recursively.call_args_list)
        self.assertEqual(times, 3)

        self.cl.SCHEMA.validate = Mock(side_effect=SchemaError('error'))
        self.cl.load_yaml('/path/to/file.yaml')
        self.cl.SCHEMA.validate.assert_called_once()
        mock_sys.exit.assert_called_once()

    def test_apply_recursively(self):
        dictionary = {1: {
                        'a': 'not called',
                        'x': {
                            'b': {
                                'y': 'z'}}}}
        expected = {1: {
                        'a': 'called',
                        'x': {
                            'b': 'called'}}}
        keywords = ['a', 'b']
        function = Mock(return_value='called')

        self.cl._apply_recursively(dictionary, keywords, function)
        self.assertEqual(dictionary, expected)

    def test_eval_function(self):
        input = 'lambda x: True'
        output = self.cl._eval_function(input)
        self.assertTrue(callable(output),
                        'returns a function defined in a string')

        input = lambda x: True
        output = self.cl._eval_function(input)
        self.assertEqual(output, input,
                         'if argument is a function, return it')

        input = 1
        self.assertRaises(TypeError, self.cl._eval_function, input,
                          'raise exception if argument contains no function')


if __name__ == "__main__":
    unittest.main(buffer=True)
