from argparse import ArgumentParser
from datetime import datetime
import json
import os
import sys
import yaml

from ._version import __version__
from .builtin import log_versions
from .execute import TempWorkDir, execute_task
from .utils.console import JsonStreams, detail
from .utils.data import Meta, Settings, DEFAULT_SETTINGS_DICT, Statistics
from .utils.template import Environment
from .validate import validate_plan


INVALID_PLAN = 251
NO_PLAN = 252


def get_args():
    parser = ArgumentParser()
    parser.add_argument(
        'plan_file',
        type=str,
        nargs='?',
        help='Load execution plan from JSON or YAML file.')
    parser.add_argument(
        '--report',
        action='store_true',
        help='Generate a HTML report.')
    parser.add_argument(
        '-t', '--tags',
        type=str,
        help='Comma separated list of tags to describe the environment.')
    parser.add_argument(
        '-T', '--temp-work-dir',
        action='store_true',
        help='Execute plan in a temporary directory.')
    parser.add_argument(
        '--version',
        action='store_true',
        help='Print version information.')
    parser.add_argument(
        '--long-version',
        action='store_true',
        help='Print detailed version information.')

    return parser.parse_args()


def load_plan_from_file(filename):
    if not filename:
        raise ValueError('No input file given.')

    with open(filename, 'r') as f:
        if filename.endswith('.json'):
            plan = json.load(f)
        elif filename.endswith('.yaml') or filename.endswith('.yml'):
            plan = yaml.load(f, Loader=yaml.SafeLoader)
        else:
            raise ValueError(
                'Failed to recognize file type. '
                'File extension must be json, yaml, or yml.')

    return plan


LOG_VERSIONS = dict(name='Log versions', log_versions={})
LOG_STATISTICS = dict(
    name='Log statistics',
    log_plan_statistics=dict(
        plan_return_value="{{ pullnrun_plan_return_value }}"))
GENERATE_REPORT = dict(
    name='Generate HTML report', generate_report=dict(
        plan_return_value="{{ pullnrun_plan_return_value }}",
        output_dir="{{ pullnrun_execdir }}"),
    when="pullnrun_generate_report")


def _get_log_builtin_vars(dict_in):
    return dict(
        name='Log builtin variables',
        echo={
            key: value for key,
            value in dict_in.items() if key.startswith('pullnrun_')})


def main(plan, report, env_tags=None, execdir=None):
    try:
        validate_plan(plan)
    except Exception as e:
        print(f'Failed to validate plan: {str(e)}')
        exit(INVALID_PLAN)

    env = Environment()
    plan_settings = Settings(DEFAULT_SETTINGS_DICT)(plan)
    stats = Statistics()
    console = JsonStreams(plan_settings.log_to_console)

    started = datetime.utcnow()
    tasks = plan.get('tasks')
    plan_tags = plan.get('tags')
    meta = Meta(plan)

    console.input(f'# Start plan execution{detail(meta.name)}')
    console.log(meta.description)

    env.register('pullnrun_python_executable', sys.executable)
    env.register('pullnrun_execdir', execdir or os.getcwd())
    env.register('pullnrun_workdir', os.getcwd())
    env.register('pullnrun_sys_platform', sys.platform)
    env.register('pullnrun_generate_report', report)
    env.register('pullnrun_environment_tags', env_tags or [])
    env.register('pullnrun_plan_tags', plan_tags or [])
    env.register('pullnrun_task_count', len(tasks))

    task_results = []

    console.input(text=f'# Run pre-tasks')
    # Pre tasks currently only includes version and builtin vars logging
    pre_settings = plan_settings(dict(register=False))
    task_results.append(execute_task(LOG_VERSIONS, pre_settings, env))
    task_results.append(
        execute_task(_get_log_builtin_vars(env.globals), pre_settings, env))

    console.input(text=f'# Run tasks')
    for i, task in enumerate(tasks, start=1):
        env.register('pullnrun_task_index', i)

        task_result = execute_task(task, plan_settings, env)

        task_results.append(task_result)
        result = task_result.get('result')
        stats.add(result)
        env.register('pullnrun_last_result', result)
        if result in ('error', 'fail',):
            break

    env.register('pullnrun_task_index', None)

    elapsed = (datetime.utcnow() - started).total_seconds()
    console.input(text=f'# Plan execution completed{detail(meta.name)}')

    plan_return_value = dict(
        **meta.json,
        started=f'{started.isoformat()}Z',
        elapsed=elapsed,
        task_return_values=task_results,
        statistics=stats.json,
        settings=plan_settings.json,
        tags=dict(
            environment=env_tags or [],
            plan=plan_tags or [],
        ),
        version=__version__,
    )
    env.register('pullnrun_plan_return_value', plan_return_value)

    console.input(text=f'# Run post-tasks')
    # Post tasks currently only includes statistics logging
    execute_task(LOG_STATISTICS, plan_settings, env)
    execute_task(GENERATE_REPORT, plan_settings, env)

    return plan_return_value


def entrypoint():
    args = get_args()
    if args.version:
        print(f'pullnrun {__version__}')
        return
    if args.long_version:
        log_versions()
        return

    try:
        plan = load_plan_from_file(args.plan_file)
    except ValueError as e:
        print(str(e))
        exit(NO_PLAN)

    tags = args.tags.split(',') if args.tags else None

    execdir = os.getcwd()
    if args.temp_work_dir:
        with TempWorkDir():
            plan = main(plan, args.report, tags, execdir)
    else:
        plan = main(plan, args.report, tags, execdir)

    stats = Statistics(plan.get('statistics'))
    exit(stats.error + stats.fail)
