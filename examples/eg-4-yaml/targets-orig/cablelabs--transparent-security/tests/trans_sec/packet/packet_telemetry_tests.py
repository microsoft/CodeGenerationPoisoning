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
import logging
import sys
import unittest
import pkg_resources
import yaml

from trans_sec.packet.packet_telemetry import PacketTelemetry

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging.getLogger('packet_telemetry_tests')


class PacketTelemetryTests(unittest.TestCase):
    """
    Tests for the PacketTelemetry class
    """

    def setUp(self):
        # Parse topology file and store into object
        topo_file = pkg_resources.resource_filename(
            'tests.trans_sec.conf', 'test_topology.yaml')
        with open(topo_file, 'r') as f:
            self.topo = yaml.safe_load(f)
            logger.info("Opened file - %s" % f.name)

        self.packet_telemetry = PacketTelemetry()

    def test_add_host(self):
        """
        Tests PacketTelemetry add_host() method that it does not raise an
        Exception
        """
        for host, host_info in self.topo['hosts'].items():
            self.packet_telemetry.add_host(
                host_info['id'], host_info['mac'],
                host_info['name'], host_info['type'])

    def test_add_switch(self):
        """
        Tests PacketTelemetry add_host() method that it does not raise an
        Exception
        """
        for switch, switch_info in self.topo['switches'].items():
            self.packet_telemetry.add_switch(
                switch_info['id'], switch_info['mac'],
                switch_info['name'], switch_info['type'])
