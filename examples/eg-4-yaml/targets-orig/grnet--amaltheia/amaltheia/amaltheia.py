#!/usr/bin/env python3

# Copyright (C) 2019  GRNET S.A.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from argparse import ArgumentParser
import sys
import yaml

import amaltheia.log as log
from amaltheia.config import config
from amaltheia.strategy import run_strategy
from amaltheia.utils import override


def parse_job(args):
    """Loads YAML file, adds any parsed arguments"""
    with open(args.script, 'r') as fin:
        result = yaml.safe_load(fin)

    for arg in args.override:
        try:
            key, value = arg.split('=')
            override(result, key, yaml.safe_load(value))
        except (ValueError, yaml.YAMLError):
            print('[amaltheia] Ignoring option {}'.format(arg))

    config.variables = {}
    for var in args.variables:
        try:
            key, value = var.split('=')
            config.variables[key] = yaml.safe_load(value)
        except (ValueError, yaml.YAMLError):
            print('[amaltheia] Ignoring variable {}'.format(var))

    for var_name in result.get('requires', []):
        if var_name not in config.variables:
            print('[amaltheia] Missing required variable {} for {}'.format(
                var_name, args.script))
            sys.exit(-1)

    return result


def amaltheia(args):
    job = parse_job(args)

    config.load(job.get('config', {}))
    log.setup(level=config.log_level)

    log.debug('[amaltheia] Loaded variables: {}'.format(config.variables))
    log.debug('[amaltheia] Loaded config: {}'.format(config._entries))

    run_strategy(job)


def main():
    parser = ArgumentParser(
        description='A system update tool for production servers')

    parser.add_argument('-s',
                        '--script',
                        required=True,
                        help='Path to amaltheia YAML script file to execute')
    parser.add_argument('-v',
                        '--variables',
                        nargs='*',
                        required=False,
                        default=[],
                        help='"key=value" pairs for script variables')
    parser.add_argument('-o',
                        '--override',
                        nargs='*',
                        required=False,
                        default=[],
                        help='"key=value" pairs for script overrides')

    amaltheia(parser.parse_args())


if __name__ == '__main__':
    main()
