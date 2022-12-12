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

import importlib
import pytest
import re
import yaml

from mock import mock
from distutils.version import StrictVersion


class SimplivityModuleTest(object):
    EXAMPLES = None

    @pytest.fixture(autouse=True)
    def setUp(self, mock_ansible_module, mock_ovc_client, request, testing_module):
        class_name = type(self).__name__

        if StrictVersion(pytest.__version__) < StrictVersion("3.6"):
            marker = request.node.get_marker('resource')
        else:
            marker = request.node.get_closest_marker('resource')

        self.resource = getattr(mock_ovc_client, "%s" % (marker.kwargs[class_name]))
        self.resource.get_by_name.return_value = self.resource
        self.mock_ovc_client = mock_ovc_client
        self.mock_ansible_module = mock_ansible_module

    @pytest.fixture
    def testing_module(self):
        resource_name = type(self).__name__.replace('Test', '')
        resource_module_path_name = self.underscore(resource_name.replace('Module', ''))

        testing_module = importlib.import_module('library.' + resource_module_path_name)
        self.testing_class = getattr(testing_module, resource_name)
        try:
            # Load scenarios from module examples (Also checks if it is a valid yaml)
