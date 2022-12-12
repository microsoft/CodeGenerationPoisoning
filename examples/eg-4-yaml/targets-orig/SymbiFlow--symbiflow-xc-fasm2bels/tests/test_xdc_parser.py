#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright 2021-2022 F4PGA Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

import unittest
from parameterized import parameterized
import pathlib
from fasm2bels.lib import parse_xdc
import yaml

XDC_PARSING_PATH = pathlib.Path(
    __file__).absolute().parent / "test_data" / "xdc_parsing"
XDC_INPUTS_PATH = XDC_PARSING_PATH / "xdc_inputs"
YAML_GOLDEN_PATH = XDC_PARSING_PATH / "yaml_golden"

TEST_NAMES = ["test_basic", "test_dict"]


class TestXdcParser(unittest.TestCase):
    @parameterized.expand(TEST_NAMES)
    def test_parse_and_compare(self, test_name):
        self.maxDiff = None

        # Get input XDC file
        xdc_path = XDC_INPUTS_PATH / (test_name + ".xdc")
        self.assertTrue(xdc_path.is_file())

        # Get golden YAML file
        yaml_path = YAML_GOLDEN_PATH / (test_name + ".yaml")
        self.assertTrue(yaml_path.is_file())

        with open(xdc_path, 'r') as fp:
            constraints = parse_xdc.parse_simple_xdc(fp)

        with open(yaml_path, 'r') as fp:
            net_props = yaml.safe_load(fp)

        all_constraints = {}
        for constraint in constraints:
            all_constraints[constraint.net] = constraint.params

        self.assertEqual(all_constraints, net_props)
