#!/usr/bin/env python

# Copyright (c) 2019 Cable Television Laboratories, Inc.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import argparse
import json
import logging
import os
import pydevd
import yaml

from trans_sec.controller.aggregate_controller import AggregateController
from trans_sec.controller.core_controller import CoreController
from trans_sec.controller.ddos_sdn_controller import (
    DdosSdnController, AGG_CTRL_KEY, CORE_CTRL_KEY)

FORMAT = '%(levelname)s %(asctime)-15s %(filename)s %(message)s'
logger = logging.getLogger('sdn_controller')


def get_args():
    default_logs = os.path.join(os.getcwd(), 'logs')
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-l', '--loglevel',
        help='Log Level <DEBUG|INFO|WARNING|ERROR> defaults to INFO',
        required=False, default='INFO')

    parser.add_argument('-f', '--logfile',
                        help='File to log to defaults to console',
                        required=False, default=None)
    parser.add_argument('-ainv', '--ansible-inventory',
                        help='The ansible inventory for applying playbooks to '
                             'the switches',
                        required=True, default=None)
    parser.add_argument('-u', '--controller-user',
                        help='The ansible user to apply playbooks to switches',
                        required=True, default=None)
    parser.add_argument('-ld', '--log-dir', type=str, required=True,
                        default=default_logs)
    parser.add_argument('-t', '--topo', help='Path to topology json',
                        required=True)
    parser.add_argument('-p', '--platform', help='Switch Platform',
                        required=True, type=str, choices=['bmv2', 'tofino'])
    parser.add_argument('-s', '--switch-config-dir', dest='switch_config_dir',
                        help='Direction with Switch configurations',
                        required=True)
    parser.add_argument('-aip', '--ae-ip', dest='ae_ip',
                        help='The IP of the machine to send drop reports',
                        required=False)
    parser.add_argument('-drf', '--drop-rpt-freq', dest='drop_rpt_freq',
                        help='The number of seconds between drop reports',
                        required=False, default=10, type=int)
    parser.add_argument('-drb', '--drop-rpt-behavior', dest='drop_rpt_behavior',
                        help='Send drop count as a delta or total value',
                        choices=['delta', 'total_count'], default='total_count')
    parser.add_argument('-dh', '--debug-host', dest='debug_host',
                        help='remote debugging host IP')
    parser.add_argument('-dp', '--debug-port', dest='debug_port', default=5678,
                        help='the remote debugging port')
    parser.add_argument('-hsp', '--http-server-port', dest='http_server_port',
                        type=int, default=9998,
                        help='the http server port defaults to 9998')
    parser.add_argument('-lp', '--load-p4', type=str, required=True,
                        choices=['True', 'False'],
                        help='When set, the controller will not attempt to '
                             'load the P4 program onto the switches')
    parser.add_argument('-ct', '--controller-type', type=str, required=True,
                        choices=['aggregate', 'core', 'full', 'lab_trial'],
                        help='When not set, all controllers will attempt to '
                             'start')
    return parser.parse_args()


def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')


def main():
    args = get_args()

    # Setup remote debugging
    if args.debug_host:
        pydevd.settrace(host=args.debug_host, port=int(args.debug_port),
                        stdoutToServer=True, stderrToServer=True)
    numeric_level = getattr(logging, args.loglevel.upper(), None)

    if args.logfile:
        logging.basicConfig(format=FORMAT, level=numeric_level,
                            filename=args.logfile)
    else:
        logging.basicConfig(format=FORMAT, level=numeric_level)

    topo_file = args.topo
    with open(topo_file, 'r') as f:
        if topo_file.endswith('json'):
            topo = json.load(f)
        else:
            topo = yaml.safe_load(f)

    logger.info(
        'Starting SDN Controller with topology - [%s] and load_p4 flag - [%s]',
        topo, eval(args.load_p4))
    controllers = dict()
    if (args.controller_type == 'aggregate'
            or args.controller_type == 'lab_trial'
            or args.controller_type == 'full'):
        logger.info('Instantiating a AggregateController')
        controllers[AGG_CTRL_KEY] = AggregateController(
            platform=args.platform,
            p4_build_out=args.switch_config_dir,
            topo=topo,
            log_dir=args.log_dir,
            load_p4=eval(args.load_p4))
    if (args.controller_type == 'core'
            or args.controller_type == 'lab_trial'
            or args.controller_type == 'full'):
        logger.info('Instantiating a CoreController')
        controllers[CORE_CTRL_KEY] = CoreController(
            platform=args.platform,
            p4_build_out=args.switch_config_dir,
            topo=topo,
            log_dir=args.log_dir,
            load_p4=eval(args.load_p4))
    drop_rpt_behavior = args.drop_rpt_behavior
    logger.info("Drop report count behavior - [%s]", drop_rpt_behavior)
    if drop_rpt_behavior == 'delta':
        is_delta = True
    else:
        is_delta = False
    controller = DdosSdnController(
        topo=topo,
        controllers=controllers,
        http_server_port=args.http_server_port,
        ansible_inventory=args.ansible_inventory,
        controller_user=args.controller_user,
        ae_ip_str=args.ae_ip,
        is_delta=is_delta)
    controller.start()


if __name__ == '__main__':
    main()
