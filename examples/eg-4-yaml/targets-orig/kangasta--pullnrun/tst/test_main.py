import json
import os
from sys import stdout
import yaml

from unittest import TestCase
from unittest.mock import patch

from _push_target import request_mock_implementation

from pullnrun.execute import TempWorkDir
from pullnrun.main import entrypoint, NO_PLAN, INVALID_PLAN
from pullnrun import __version__

TST_DIR = os.path.dirname(os.path.realpath(__file__))

class TestConsole:
    def __init__(self):
        self.content = ''

    def print_mock_implementation(self, *args, **kwargs):
        self.content += ' '.join(str(a) for a in args) + '\n'

class TestExit(Exception):
    def __init__(self, exit_code):
        super().__init__()
        self.exit_code = exit_code

def exit_mock_implementation(exit_code):
    raise TestExit(exit_code)

class MainTest(TestCase):
    @patch('builtins.exit')
    @patch('builtins.print')
    def test_main_version(self, print_mock, exit_mock):
        with patch('sys.argv', ['pullnrun', '--version']):
            entrypoint()

        print_mock.assert_called_with(f'pullnrun {__version__}')

    @patch('builtins.exit', side_effect=exit_mock_implementation)
    @patch('builtins.print')
    def test_main_exit_codes(self, print_mock, exit_mock):
        for args, exit_code in [
            ([], NO_PLAN),
            ([f'{TST_DIR}/invalid_plan.yml'], INVALID_PLAN),
        ]:
            with self.assertRaises(TestExit):
                with patch('sys.argv', ['pullnrun', *args]):
                    entrypoint()

            exit_mock.assert_called_with(exit_code)

    @patch('builtins.exit')
    @patch('builtins.print')
    def test_main_errors(self, print_mock, exit_mock):
        console = TestConsole()
        print_mock.side_effect = console.print_mock_implementation

        with patch('sys.argv', ['pullnrun', f'{TST_DIR}/../examples/errors.yml']):
            entrypoint()

        print_mock.assert_any_call(f'pullnrun {__version__}', file=stdout)
        exit_mock.assert_called_with(1)
        self.assertRegex(console.content, r'Ignored:\s*1')

    @patch('builtins.exit')
    @patch('builtins.print')
    def test_main_pull_http(self, print_mock, exit_mock):
        with TempWorkDir():
            with patch('sys.argv', ['pullnrun', f'{TST_DIR}/../examples/fizzbuzz.json']):
                entrypoint()

            exit_mock.assert_called_with(0)

    @patch('builtins.exit')
    @patch('builtins.print')
    def test_main_pull_git(self, print_mock, exit_mock):
        with TempWorkDir():
            with patch('sys.argv', ['pullnrun', f'{TST_DIR}/../examples/fizzbuzz_git.json']):
                entrypoint()

            exit_mock.assert_called_with(0)

    @patch('builtins.exit')
    @patch('builtins.print')
    @patch('pullnrun.builtin._push.request')
    def test_main_push_http(self, request_mock, print_mock, exit_mock):
        request_mock.side_effect = request_mock_implementation
        with TempWorkDir():
            with open('test_file.txt', 'w') as f:
                f.write('test_content')

            with patch('sys.argv', ['pullnrun', f'{TST_DIR}/../examples/push.yml']):
                entrypoint()

        exit_mock.assert_called_with(1)

    @patch('builtins.exit')
    @patch('builtins.print')
    def test_main_invalid_tasks(self, print_mock, exit_mock):
        console = TestConsole()
        print_mock.side_effect = console.print_mock_implementation

        with TempWorkDir():
            with patch('sys.argv', ['pullnrun', f'{TST_DIR}/invalid_tasks.yml']):
                entrypoint()

        exit_mock.assert_called_with(0)
        self.assertRegex(console.content, r'Ignored:\s*4')
        for i in [0, 2]:
            self.assertIn(f'Task must contain exactly one function key, but {i} were given', console.content)
        self.assertIn('Function not found for cow.', console.content)
        self.assertIn('Caught error raised from task', console.content)

    @patch('builtins.exit')
    @patch('builtins.print')
    def test_main_invalid_task_stop_on_errors(self, print_mock, exit_mock):
        console = TestConsole()
        print_mock.side_effect = console.print_mock_implementation

        with open(f'{TST_DIR}/invalid_tasks.yml', 'r') as f:
            plan = yaml.load(f, Loader=yaml.SafeLoader)
            tasks = plan.get('tasks')

        for task in tasks:
            with TempWorkDir() as tmp_dir_path:
                with open('plan.yml', 'w') as f:
                    json.dump(dict(tasks=[task]), f)

                with patch('sys.argv', ['pullnrun', f'{tmp_dir_path}/plan.yml']):
                    entrypoint()

            exit_mock.assert_called_with(1)

    @patch('builtins.exit')
    @patch('builtins.print')
    def test_main_when(self, print_mock, exit_mock):
        console = TestConsole()
        print_mock.side_effect = console.print_mock_implementation

        with TempWorkDir():
            with patch('sys.argv', ['pullnrun', f'{TST_DIR}/../examples/when.yml']):
                entrypoint()

        exit_mock.assert_called_with(0)
        self.assertRegex(console.content, r'Skipped:\s*3')
        self.assertRegex(console.content, r'Ignored:\s*1')

    @patch('builtins.exit')
    @patch('builtins.print')
    def test_main_tmp_work_dir(self, print_mock, exit_mock):
        with TempWorkDir():
            with patch('sys.argv', ['pullnrun', '-T', '--report', f'{TST_DIR}/../examples/fizzbuzz.json']):
                entrypoint()

            dir_ = os.listdir()
            self.assertIn('pullnrun_report.html', dir_)
            self.assertNotIn('fizzbuzz.py', dir_)
