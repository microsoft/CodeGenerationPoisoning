#!/usr/bin/env python
#
# Copyright 2018 the original author or authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Ponsim OLT Adapter main entry point"""

import argparse
import os
import time

import arrow
import yaml
from packaging.version import Version
from simplejson import dumps
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.task import LoopingCall
from zope.interface import implementer

from pyvoltha.common.structlog_setup import setup_logging, update_logging
from pyvoltha.common.utils.asleep import asleep
from pyvoltha.common.utils.deferred_utils import TimeOutError
from pyvoltha.common.utils.dockerhelpers import get_my_containers_name
from pyvoltha.common.utils.nethelpers import get_my_primary_local_ipv4, \
    get_my_primary_interface
from pyvoltha.common.utils.registry import registry, IComponent
from pyvoltha.adapters.kafka.adapter_proxy import AdapterProxy
from pyvoltha.adapters.kafka.adapter_request_facade import AdapterRequestFacade
from pyvoltha.adapters.kafka.core_proxy import CoreProxy
from pyvoltha.adapters.kafka.kafka_inter_container_library import IKafkaMessagingProxy, \
    get_messaging_proxy
from pyvoltha.adapters.kafka.kafka_proxy import KafkaProxy, get_kafka_proxy
from ponsim_olt import PonSimOltAdapter
from voltha_protos.adapter_pb2 import AdapterConfig

defs = dict(
    version_file='./VERSION',
    config=os.environ.get('CONFIG', './ponsim_olt.yml'),
    container_name_regex=os.environ.get('CONTAINER_NUMBER_EXTRACTOR', '^.*\.(['
                                                                      '0-9]+)\..*$'),
    consul=os.environ.get('CONSUL', 'localhost:8500'),
    name=os.environ.get('NAME', 'ponsim_olt'),
    vendor=os.environ.get('VENDOR', 'Voltha Project'),
    device_type=os.environ.get('DEVICE_TYPE', 'ponsim_olt'),
    accept_bulk_flow=os.environ.get('ACCEPT_BULK_FLOW', True),
    accept_atomic_flow=os.environ.get('ACCEPT_ATOMIC_FLOW', True),
    etcd=os.environ.get('ETCD', 'localhost:2379'),
    core_topic=os.environ.get('CORE_TOPIC', 'rwcore'),
    interface=os.environ.get('INTERFACE', get_my_primary_interface()),
    instance_id=os.environ.get('INSTANCE_ID', os.environ.get('HOSTNAME', '1')),
    kafka_adapter=os.environ.get('KAFKA_ADAPTER', '172.20.10.3:9092'),
    kafka_cluster=os.environ.get('KAFKA_CLUSTER', '172.20.10.3:9092'),
    backend=os.environ.get('BACKEND', 'none'),
    retry_interval=os.environ.get('RETRY_INTERVAL', 2),
    heartbeat_topic=os.environ.get('HEARTBEAT_TOPIC', "adapters.heartbeat"),
)


def parse_args():
    parser = argparse.ArgumentParser()

    _help = ('Path to ponsim_onu.yml config file (default: %s). '
             'If relative, it is relative to main.py of ponsim adapter.'
             % defs['config'])
    parser.add_argument('-c', '--config',
                        dest='config',
                        action='store',
                        default=defs['config'],
                        help=_help)

    _help = 'Regular expression for extracting conatiner number from ' \
            'container name (default: %s)' % defs['container_name_regex']
    parser.add_argument('-X', '--container-number-extractor',
                        dest='container_name_regex',
                        action='store',
                        default=defs['container_name_regex'],
                        help=_help)

    _help = '<hostname>:<port> to consul agent (default: %s)' % defs['consul']
    parser.add_argument('-C', '--consul',
                        dest='consul',
                        action='store',
                        default=defs['consul'],
                        help=_help)

    _help = 'name of this adapter (default: %s)' % defs['name']
    parser.add_argument('-na', '--name',
                        dest='name',
                        action='store',
                        default=defs['name'],
                        help=_help)

    _help = 'vendor of this adapter (default: %s)' % defs['vendor']
    parser.add_argument('-ven', '--vendor',
                        dest='vendor',
                        action='store',
                        default=defs['vendor'],
                        help=_help)

    _help = 'supported device type of this adapter (default: %s)' % defs[
        'device_type']
    parser.add_argument('-dt', '--device_type',
                        dest='device_type',
                        action='store',
                        default=defs['device_type'],
                        help=_help)

    _help = 'specifies whether the device type accepts bulk flow updates ' \
            'adapter (default: %s)' % defs['accept_bulk_flow']
    parser.add_argument('-abf', '--accept_bulk_flow',
                        dest='accept_bulk_flow',
                        action='store',
                        default=defs['accept_bulk_flow'],
                        help=_help)

    _help = 'specifies whether the device type accepts add/remove flow ' \
            '(default: %s)' % defs['accept_atomic_flow']
    parser.add_argument('-aaf', '--accept_atomic_flow',
                        dest='accept_atomic_flow',
                        action='store',
                        default=defs['accept_atomic_flow'],
                        help=_help)

    _help = '<hostname>:<port> to etcd server (default: %s)' % defs['etcd']
    parser.add_argument('-e', '--etcd',
                        dest='etcd',
                        action='store',
                        default=defs['etcd'],
                        help=_help)

    _help = ('unique string id of this container instance (default: %s)'
             % defs['instance_id'])
    parser.add_argument('-i', '--instance-id',
                        dest='instance_id',
                        action='store',
                        default=defs['instance_id'],
                        help=_help)

    _help = 'ETH interface to recieve (default: %s)' % defs['interface']
    parser.add_argument('-I', '--interface',
                        dest='interface',
                        action='store',
                        default=defs['interface'],
                        help=_help)

    _help = 'omit startup banner log lines'
    parser.add_argument('-n', '--no-banner',
                        dest='no_banner',
                        action='store_true',
                        default=False,
                        help=_help)

    _help = 'do not emit periodic heartbeat log messages'
    parser.add_argument('-N', '--no-heartbeat',
                        dest='no_heartbeat',
                        action='store_true',
                        default=False,
                        help=_help)

    _help = "suppress debug and info logs"
    parser.add_argument('-q', '--quiet',
                        dest='quiet',
                        action='count',
                        help=_help)

    _help = 'enable verbose logging'
    parser.add_argument('-v', '--verbose',
                        dest='verbose',
                        action='count',
                        help=_help)

    _help = ('use docker container name as conatiner instance id'
             ' (overrides -i/--instance-id option)')
    parser.add_argument('--instance-id-is-container-name',
                        dest='instance_id_is_container_name',
                        action='store_true',
                        default=False,
                        help=_help)

    _help = ('<hostname>:<port> of the kafka adapter broker (default: %s). ('
             'If not '
             'specified (None), the address from the config file is used'
             % defs['kafka_adapter'])
    parser.add_argument('-KA', '--kafka_adapter',
                        dest='kafka_adapter',
                        action='store',
                        default=defs['kafka_adapter'],
                        help=_help)

    _help = ('<hostname>:<port> of the kafka cluster broker (default: %s). ('
             'If not '
             'specified (None), the address from the config file is used'
             % defs['kafka_cluster'])
    parser.add_argument('-KC', '--kafka_cluster',
                        dest='kafka_cluster',
                        action='store',
                        default=defs['kafka_cluster'],
                        help=_help)

    _help = 'backend to use for config persitence'
    parser.add_argument('-b', '--backend',
                        default=defs['backend'],
                        choices=['none', 'consul', 'etcd'],
                        help=_help)

    _help = 'topic of core on the kafka bus'
    parser.add_argument('-ct', '--core_topic',
                        dest='core_topic',
                        action='store',
                        default=defs['core_topic'],
                        help=_help)

    args = parser.parse_args()

    # post-processing

    if args.instance_id_is_container_name:
        args.instance_id = get_my_containers_name()

    return args


def load_config(args):
    path = args.config
    if path.startswith('.'):
        dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(dir, path)
    path = os.path.abspath(path)
    with open(path) as fd:
        config = yaml.load(fd)
    return config


def print_banner(log):
    log.info(' ____                 _              ___  _   _____   ')
    log.info('|  _ \ ___  _ __  ___(_)_ __ ___    / _ \| | |_   _|  ')
    log.info('| |_) / _ \| \'_ \/ __| | \'_ ` _ \  | | | | |   | |  ')
    log.info('|  __/ (_) | | | \__ \ | | | | | | | |_| | |___| |    ')
    log.info('|_|   \___/|_| |_|___/_|_| |_| |_|  \___/|_____|_|    ')
    log.info('                                                      ')
    log.info('   _       _             _                            ')
    log.info('  / \   __| | __ _ _ __ | |_ ___ _ __                 ')
    log.info('  / _ \ / _` |/ _` | \'_ \| __/ _ \ \'__|             ')
    log.info(' / ___ \ (_| | (_| | |_) | ||  __/ |                  ')
    log.info('/_/   \_\__,_|\__,_| .__/ \__\___|_|                  ')
    log.info('                   |_|                                ')
    log.info('(to stop: press Ctrl-C)')


@implementer(IComponent)
class Main(object):

    def __init__(self):

        self.args = args = parse_args()
        self.config = load_config(args)

        verbosity_adjust = (args.verbose or 0) - (args.quiet or 0)
        self.log = setup_logging(self.config.get('logging', {}),
                                 args.instance_id,
                                 verbosity_adjust=verbosity_adjust)
        self.log.info('container-number-extractor',
                      regex=args.container_name_regex)

        self.ponsim_olt_adapter_version = self.get_version()
        self.log.info('Ponsim-OLT-Adapter-Version', version=
        self.ponsim_olt_adapter_version)

        if not args.no_banner:
            print_banner(self.log)

        self.adapter = None
        # Create a unique instance id using the passed-in instance id and
        # UTC timestamp
        current_time = arrow.utcnow().timestamp
        self.instance_id = self.args.instance_id + '_' + str(current_time)

        self.core_topic = args.core_topic
        self.listening_topic = args.name
        self.startup_components()

        if not args.no_heartbeat:
            self.start_heartbeat()
            self.start_kafka_cluster_heartbeat(self.instance_id)

    def get_version(self):
        path = defs['version_file']
        if not path.startswith('/'):
            dir = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(dir, path)

        path = os.path.abspath(path)
        version_file = open(path, 'r')
        v = version_file.read()

        # Use Version to validate the version string - exception will be raised
        # if the version is invalid
        Version(v)

        version_file.close()
        return v

    def start(self):
        self.start_reactor()  # will not return except Keyboard interrupt

    def stop(self):
        pass

    def get_args(self):
        """Allow access to command line args"""
        return self.args

    def get_config(self):
        """Allow access to content of config file"""
        return self.config

    def _get_adapter_config(self):
        cfg = AdapterConfig()
        return cfg

    @inlineCallbacks
    def startup_components(self):
        try:
            self.log.info('starting-internal-components',
                          consul=self.args.consul,
                          etcd=self.args.etcd)

            registry.register('main', self)

            # Update the logger to output the vcore id.
            self.log = update_logging(instance_id=self.instance_id,
                                      vcore_id=None)

            yield registry.register(
                'kafka_cluster_proxy',
                KafkaProxy(
                    self.args.consul,
                    self.args.kafka_cluster,
                    config=self.config.get('kafka-cluster-proxy', {})
                )
            ).start()

            config = self._get_adapter_config()

            self.core_proxy = CoreProxy(
                kafka_proxy=None,
                default_core_topic=self.core_topic,
                my_listening_topic=self.listening_topic)

            self.adapter_proxy = AdapterProxy(
                kafka_proxy=None,
                core_topic=self.core_topic,
                my_listening_topic=self.listening_topic)

            self.adapter = PonSimOltAdapter(core_proxy=self.core_proxy,
                                            adapter_proxy=self.adapter_proxy,
                                            config=config)

            ponsim_request_handler = AdapterRequestFacade(adapter=self.adapter,
                                                    core_proxy=self.core_proxy)

            yield registry.register(
                'kafka_adapter_proxy',
                IKafkaMessagingProxy(
                    kafka_host_port=self.args.kafka_adapter,
                    # TODO: Add KV Store object reference
                    kv_store=self.args.backend,
                    default_topic=self.args.name,
                    group_id_prefix=self.args.instance_id,
                    target_cls=ponsim_request_handler
                )
            ).start()

            self.core_proxy.kafka_proxy = get_messaging_proxy()
            self.adapter_proxy.kafka_proxy = get_messaging_proxy()

            # retry for ever
            res = yield self._register_with_core(-1)

            self.log.info('started-internal-services')

        except Exception as e:
            self.log.exception('Failure-to-start-all-components', e=e)

    @inlineCallbacks
    def shutdown_components(self):
        """Execute before the reactor is shut down"""
        self.log.info('exiting-on-keyboard-interrupt')
        for component in reversed(registry.iterate()):
            yield component.stop()

        import threading
        self.log.info('THREADS:')
        main_thread = threading.current_thread()
        for t in threading.enumerate():
            if t is main_thread:
                continue
            if not t.isDaemon():
                continue
            self.log.info('joining thread {} {}'.format(
                t.getName(), "daemon" if t.isDaemon() else "not-daemon"))
            t.join()

    def start_reactor(self):
        from twisted.internet import reactor
        reactor.callWhenRunning(
            lambda: self.log.info('twisted-reactor-started'))
        reactor.addSystemEventTrigger('before', 'shutdown',
                                      self.shutdown_components)
        reactor.run()

    @inlineCallbacks
    def _register_with_core(self, retries):
        while 1:
            try:
                resp = yield self.core_proxy.register(
                    self.adapter.adapter_descriptor(),
                    self.adapter.device_types())
                if resp:
                    self.log.info('registered-with-core',
                                  coreId=resp.instance_id)
                returnValue(resp)
            except TimeOutError as e:
                self.log.warn("timeout-when-registering-with-core", e=e)
                if retries == 0:
                    self.log.exception("no-more-retries", e=e)
                    raise
                else:
                    retries = retries if retries < 0 else retries - 1
                    yield asleep(defs['retry_interval'])
            except Exception as e:
                self.log.exception("failed-registration", e=e)
                raise

    def start_heartbeat(self):

        t0 = time.time()
        t0s = time.ctime(t0)

        def heartbeat():
            self.log.debug(status='up', since=t0s, uptime=time.time() - t0)

        lc = LoopingCall(heartbeat)
        lc.start(10)

    # Temporary function to send a heartbeat message to the external kafka
    # broker
    def start_kafka_cluster_heartbeat(self, instance_id):
        # For heartbeat we will send a message to a specific "voltha-heartbeat"
        #  topic.  The message is a protocol buf
        # message
        message = dict(
            type='heartbeat',
            adapter=self.args.name,
            instance=instance_id,
            ip=get_my_primary_local_ipv4()
        )
        topic = defs['heartbeat_topic']

        def send_msg(start_time):
            try:
                kafka_cluster_proxy = get_kafka_proxy()
                if kafka_cluster_proxy and not kafka_cluster_proxy.is_faulty():
                    # self.log.debug('kafka-proxy-available')
                    message['ts'] = arrow.utcnow().timestamp
                    message['uptime'] = time.time() - start_time
                    # self.log.debug('start-kafka-heartbeat')
                    kafka_cluster_proxy.send_message(topic, dumps(message))
                else:
                    self.log.error('kafka-proxy-unavailable')
            except Exception, e:
                self.log.exception('failed-sending-message-heartbeat', e=e)

        try:
            t0 = time.time()
            lc = LoopingCall(send_msg, t0)
            lc.start(10)
        except Exception, e:
            self.log.exception('failed-kafka-heartbeat', e=e)


if __name__ == '__main__':
    Main().start()
