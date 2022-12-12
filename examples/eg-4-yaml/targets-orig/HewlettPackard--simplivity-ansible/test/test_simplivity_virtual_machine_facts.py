#!/usr/bin/python
# -*- coding: utf-8 -*-
###
# Copyright (2019) Hewlett Packard Enterprise Development LP
#
# Licensed under the Apache License, Version 2.0 (the "License");
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
###
import mock
import pytest
import yaml

from simplivity_test_utils import SimplivityModuleFactsTest
from simplivity_module_loader import VirtualMachineFactsModule


PARAMS_GET_ALL = """
    config: "{{ config.json }}"
    name: null
"""

PARAMS_GET_BY_NAME = """
    config: "{{ config.json }}"
    name: "TestVM"
"""

PARAMS_GET_ALL_WITH_OPTIONS = """
    config: "{{ config.json }}"
    name: "TestVM"
    options:
      - backups
"""


@pytest.mark.resource(TestVirtualMachineFactsModule='virtual_machines')
class TestVirtualMachineFactsModule(SimplivityModuleFactsTest):

    def test_should_get_all_vms(self):
        vm = mock.Mock()
        vm.data = {'name': 'TESVM', 'id': '1234'}

        self.mock_ansible_module.params = yaml.load(PARAMS_GET_ALL)
        self.resource.get_all.return_value = [vm]

        VirtualMachineFactsModule().run()

        self.mock_ansible_module.exit_json.assert_called_once_with(
            changed=False,
            ansible_facts=dict(virtual_machines=[vm.data])
        )

    def test_should_get_vm_by_name(self):
        vm = mock.Mock()
        vm.data = {'name': 'TESTVM', 'id': 1234}

        self.resource.get_by_name.return_value = vm
        self.mock_ansible_module.params = yaml.load(PARAMS_GET_BY_NAME)

        VirtualMachineFactsModule().run()

        self.mock_ansible_module.exit_json.assert_called_once_with(
            changed=False,
            ansible_facts=dict(virtual_machines=[vm.data])
        )

    def test_backups(self):
        backup = mock.Mock()
        backup.data = {'name': 'TESTBACKUP', 'id': 1234}
        vm = mock.Mock()
        vm.data = {'name': 'TESTVM', 'id': 1234}

        self.resource.get_by_name.return_value = vm
        vm.get_backups.return_value = [backup]

        self.mock_ansible_module.params = yaml.load(PARAMS_GET_ALL_WITH_OPTIONS)

        VirtualMachineFactsModule().run()

        self.mock_ansible_module.exit_json.assert_called_once_with(
            changed=False,
            ansible_facts=dict(virtual_machines=[vm.data], backups=[backup.data])
        )


if __name__ == '__main__':
    pytest.main([__file__])
