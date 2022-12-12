import os
import yaml

from jinja2.exceptions import UndefinedError

from unittest import TestCase

from pullnrun.utils.template import Environment

TST_DIR = os.path.dirname(os.path.realpath(__file__))
with open(f'{TST_DIR}/template_test_data.yml', 'r') as f:
    TEST_DATA = yaml.load(f, Loader=yaml.SafeLoader)

class TemplateTest(TestCase):
    def test_template(self):
        env = Environment()
        for key, value in TEST_DATA.get('vars').items():
            env.register(key, value)

        for test in TEST_DATA.get('tests'):
            in_ = test.get('in')
            out = test.get('out')

            r = env.resolve_templates(in_)
            self.assertEqual(r, out)

    def test_undefined(self):
        env = Environment()
        with self.assertRaises(UndefinedError):
            env.resolve_templates('{{ undefined_var }}')
