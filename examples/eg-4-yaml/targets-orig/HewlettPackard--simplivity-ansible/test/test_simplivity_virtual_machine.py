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

from copy import deepcopy
from simplivity_test_utils import SimplivityModuleTest
from simplivity_module_loader import VirtualMachineModule
from simplivity.exceptions import HPESimpliVityResourceNotFound


PARAMS_FOR_SET_POLICY_FOR_MULTIPLE_VMS = """
    config: "{{ config }}"
    state: set_policy_for_multiple_vms
    data:
      vm_names:
        - 'TESTVM1'
        - 'TESTVM2'
      policy_name: 'TESTPOLICY'
"""

PARAMS_FOR_CLONE = """
    config: "{{ config }}"
    state: clone
    data:
      name: 'TESTVM'
      new_name: 'TESTVM_CLONE'
"""

PARAMS_FOR_MOVE = """
    config: "{{ config }}"
    state: move
    data:
      name: 'TESTVM'
      new_name: 'TESTVM_MOVE'
      datastore_name: 'TEST_DATASTORE_NAME'
"""

PARAMS_FOR_BACKUP = """
    config: "{{ config }}"
    state: backup
    data:
      name: 'TESTVM'
      backup_name: 'TESTBACKUP'
      cluster_name: null
      app_consistent: false
      consistency_type: null
"""

PARAMS_FOR_BACKUP_PARAMETERS = """
    config: "{{ config }}"
    state: set_backup_parameters
    data:
      name: 'TESTVM'
      guest_username: 'guest_username'
      guest_password: 'guest_password'
      override_guest_validation: false
      app_aware_type: null
"""

PARAMS_FOR_SET_POLICY = """
    config: "{{ config }}"
    state: set_policy
    data:
      name: 'TESTPOLICY'
      policy_name: 'POLICY_NAME'
"""


@pytest.mark.resource(TestVirtualMachineModule='virtual_machines')
class TestVirtualMachineModule(SimplivityModuleTest):
    @pytest.fixture(autouse=True)
    def specific_setup(self):
        self.vm1 = mock.Mock()
        self.vm1.data = {'name': 'TESTVM1', 'id': '123'}
        self.vm2 = mock.Mock()
        self.vm2.data = {'name': 'TESTVM2', 'id': '345'}
        self.policy = mock.Mock()
        self.policy.data = {'name': 'policy', 'id': '123'}

    def test_set_policy_with_no_vms_already_have_the_policy(self):
        self.mock_ansible_module.params = yaml.load(PARAMS_FOR_SET_POLICY_FOR_MULTIPLE_VMS)
        self.policy.get_vms.return_value = []
        self.mock_ovc_client.virtual_machines.get_by_name.side_effect = [self.vm1, self.vm2]
        self.mock_ovc_client.policies.get_by_name.return_value = self.policy

        VirtualMachineModule().run()

        self.mock_ansible_module.exit_json.assert_called_once_with(
            changed=True,
            msg=VirtualMachineModule.MSG_UPDATED_POLICY_OF_MULTIPLE_VMS,
            ansible_facts=dict(policy_updated_vms=[self.vm1.data["name"], self.vm2.data["name"]])
        )

    def test_set_policy_should_avoid_vms_that_alreay_have_the_policy(self):
        self.mock_ansible_module.params = yaml.load(PARAMS_FOR_SET_POLICY_FOR_MULTIPLE_VMS)
        self.policy.get_vms.return_value = [self.vm1]
        self.mock_ovc_client.virtual_machines.get_by_name.side_effect = [self.vm1, self.vm2]
        self.mock_ovc_client.policies.get_by_name.return_value = self.policy

        VirtualMachineModule().run()

        self.mock_ansible_module.exit_json.assert_called_once_with(
            changed=True,
            msg=VirtualMachineModule.MSG_UPDATED_POLICY_OF_MULTIPLE_VMS,
            ansible_facts=dict(policy_updated_vms=[self.vm2.data["name"]])
        )

    def test_set_policy_should_not_call_when_all_the_vms_have_policy_already_attached(self):
        self.mock_ansible_module.params = yaml.load(PARAMS_FOR_SET_POLICY_FOR_MULTIPLE_VMS)
        self.policy.get_vms.return_value = [self.vm1, self.vm2]
        self.mock_ovc_client.virtual_machines.get_by_name.side_effect = [self.vm1, self.vm2]
        self.mock_ovc_client.policies.get_by_name.return_value = self.policy

        VirtualMachineModule().run()

        self.mock_ansible_module.exit_json.assert_called_once_with(
            changed=False,
            msg=VirtualMachineModule.MSG_POLICY_ALREADY_APPLIED,
            ansible_facts=dict(policy_updated_vms=[])
        )

    def test_clone_when_vm_with_the_same_name_exists(self):
        self.mock_ansible_module.params = yaml.load(PARAMS_FOR_CLONE)
        self.mock_ovc_client.virtual_machines.get_by_name.return_value = self.vm1

        VirtualMachineModule().run()

        self.mock_ansible_module.exit_json.assert_called_once_with(
            changed=False,
            msg=VirtualMachineModule.MSG_VM_WITH_SAME_NAME_EXISTS,
            ansible_facts=dict(cloned_vm={})
        )

    def test_clone_should_work_if_vm_name_is_available(self):
        self.mock_ansible_module.params = yaml.load(PARAMS_FOR_CLONE)

        self.mock_ovc_client.virtual_machines.get_by_name.side_effect = [self.vm1, HPESimpliVityResourceNotFound('Test')]
        self.vm1.clone.return_value = self.vm2

        VirtualMachineModule().run()

        self.mock_ansible_module.exit_json.assert_called_once_with(
            changed=True,
            msg=VirtualMachineModule.MSG_CLONED_SUCCESSFULLY,
            ansible_facts=dict(cloned_vm=self.vm2.data)
        )

    def test_move_when_vm_with_the_same_name_exists(self):
        self.mock_ansible_module.params = yaml.load(PARAMS_FOR_MOVE)
        self.mock_ovc_client.virtual_machines.get_by_name.return_value = self.vm1

        VirtualMachineModule().run()

        self.mock_ansible_module.exit_json.assert_called_once_with(
            changed=False,
            msg=VirtualMachineModule.MSG_VM_WITH_SAME_NAME_EXISTS,
            ansible_facts=dict(moved_vm={})
        )

    def test_move_should_work_if_vm_name_is_available(self):
        self.mock_ansible_module.params = yaml.load(PARAMS_FOR_MOVE)
        self.mock_ovc_client.virtual_machines.get_all.return_value = None
        self.mock_ovc_client.virtual_machines.get_by_name.return_value = self.vm1
        self.vm1.move.return_value = self.vm2

        VirtualMachineModule().run()

        self.mock_ansible_module.exit_json.assert_called_once_with(
            changed=True,
            msg=VirtualMachineModule.MSG_MOVED_SUCCESSFULLY,
            ansible_facts=dict(moved_vm=self.vm2.data)
        )

    def test_create_backup_when_name_is_not_available(self):
        backup = mock.Mock()
        backup.data = {'name': 'TESTBACK', 'id': '123'}

        self.mock_ansible_module.params = yaml.load(PARAMS_FOR_BACKUP)
        self.mock_ovc_client.virtual_machines.get_by_name.return_value = self.vm1
        self.mock_ovc_client.backups.get_by_name.return_value = backup

        VirtualMachineModule().run()

        self.mock_ansible_module.exit_json.assert_called_once_with(
            changed=False,
            msg=VirtualMachineModule.MSG_BACKUP_EXISTS,
            ansible_facts=dict(backup={})
        )

    def test_create_backup_when_backup_name_is_available(self):
        backup = mock.Mock()
        backup.data = {'name': 'TESTBACK', 'id': '123'}

        self.mock_ansible_module.params = yaml.load(PARAMS_FOR_BACKUP)
        self.mock_ovc_client.virtual_machines.get_by_name.return_value = self.vm1
        self.mock_ovc_client.backups.get_by_name.side_effect = HPESimpliVityResourceNotFound('Test')
        self.vm1.create_backup.return_value = backup

        VirtualMachineModule().run()

        self.mock_ansible_module.exit_json.assert_called_once_with(
            changed=True,
            msg=VirtualMachineModule.MSG_BACKUP_CREATED,
            ansible_facts=dict(backup=backup.data)
        )

    def test_create_backup_parameters(self):
        self.mock_ansible_module.params = yaml.load(PARAMS_FOR_BACKUP_PARAMETERS)
        self.mock_ovc_client.virtual_machines.get_by_name.return_value = self.vm1

        VirtualMachineModule().run()

        self.mock_ansible_module.exit_json.assert_called_once_with(
            changed=True,
            msg=VirtualMachineModule.MSG_CREATED_BACKUP_PARAMETERS,
            ansible_facts=dict(virtual_machine=self.vm1.data)
        )

    def test_set_policy(self):
        policy = mock.Mock()
        policy.data = {'name': 'TESTPOLICY', 'id': '123'}

        self.mock_ansible_module.params = yaml.load(PARAMS_FOR_SET_POLICY)
        self.mock_ovc_client.virtual_machines.get_by_name.return_value = self.vm1
        self.mock_ovc_client.policies.get_by_name.return_value = policy
        policy.get_vms.return_value = [self.vm2]

        VirtualMachineModule().run()

        self.mock_ansible_module.exit_json.assert_called_once_with(
            changed=True,
            msg=VirtualMachineModule.MSG_SET_VM_POLICY,
            ansible_facts=dict(virtual_machine=self.vm1.data)
        )

    def test_set_policy_when_policy_already_attached_to_vm(self):
        policy = mock.Mock()
        policy.data = {'name': 'TESTPOLICY', 'id': '123'}

        self.mock_ansible_module.params = yaml.load(PARAMS_FOR_SET_POLICY)
        self.mock_ovc_client.virtual_machines.get_by_name.return_value = self.vm1
        self.mock_ovc_client.policies.get_by_name.return_value = policy
        policy.get_vms.return_value = [self.vm1]

        VirtualMachineModule().run()

        self.mock_ansible_module.exit_json.assert_called_once_with(
            changed=False,
            msg=VirtualMachineModule.MSG_VM_POLICY_ALREADY_APPLIED,
            ansible_facts=dict(virtual_machine={})
        )


if __name__ == '__main__':
    pytest.main([__file__])
