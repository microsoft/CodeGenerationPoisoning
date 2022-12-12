"""
Unit tests for util/run_patch_builds.py.

Most of the functionality of multi_patch_builds.py would require an evergreen client in PATH,
and also a checked out mongo git repo, and we don't want to create such complex infrastructure.
But some superficial unit testing is still possible and meaningful to execute.
"""


import os
import unittest

import yaml

from dsi.multi_patch_builds import MultiEvergreen
from test_lib.fixture_files import FixtureFiles
from test_lib.test_requests_parent import TestRequestsParent

FIXTURE = FixtureFiles()


class TestMultiEvergreen(TestRequestsParent):
    """
    Test the MultiEvergreen client class.
    """

    @classmethod
    def tearDownClass(cls):
        """Remove test output file"""
        os.remove("5873a2613ff1224e8e0003ea.yml")

    def test_parse_options(self):
        """MultiEvergreen: parse options."""
        expected = {
            "project": "sys-perf",
            "large": False,
            "cancel_patch": False,
            "tasks": ["core_workloads_WT", "core_workloads_MMAPv1"],
            "description": "PERF-814 Unit test, please ignore",
            "finalize": False,
            "variants": ["linux-standalone", "linux-1-node-replSet"],
            "mongo_repo": ".",
            "evergreen_config": FIXTURE.repo_root_file_path("config.yml"),
            "n": 2,
            "result_urls": False,
        }
        args = [
            "--description",
            "PERF-814 Unit test, please ignore",
            "-n",
            "2",
            "--variants",
            "linux-standalone",
            "--variants",
            "linux-1-node-replSet",
            "--tasks",
            "core_workloads_WT",
            "--tasks",
            "core_workloads_MMAPv1",
        ]
        client = MultiEvergreen(args)
        client.config["evergreen_config"] = FIXTURE.repo_root_file_path("config.yml")
        client.parse_options()
        self.assertEqual(client.config, expected)

    def test_evergreen_patch_compile_cmd(self):
        """MultiEvergreen: compile cmd for evergreen patch."""
        expected1 = [
            "evergreen",
            "patch",
            "--description",
            "PERF-814 Unit test, please ignore #2",
            "--yes",
            "--project",
            "sys-perf",
            "--variants",
            "linux-standalone",
            "--variants",
            "linux-1-node-replSet",
            "--tasks",
            "core_workloads_WT",
            "--tasks",
            "core_workloads_MMAPv1",
        ]
        expected2 = [
            "evergreen",
            "patch",
            "--description",
            "PERF-814 Unit test, please ignore #3",
            "--yes",
            "--project",
            "sys-perf",
            "--variants",
            "linux-standalone",
            "--variants",
            "linux-1-node-replSet",
            "--tasks",
            "core_workloads_WT",
            "--tasks",
            "core_workloads_MMAPv1",
        ]
        client = MultiEvergreen()
        client.config = {
            "project": "sys-perf",
            "large": False,
            "cancel_patch": False,
            "tasks": ["core_workloads_WT", "core_workloads_MMAPv1"],
            "description": "PERF-814 Unit test, please ignore",
            "finalize": False,
            "variants": ["linux-standalone", "linux-1-node-replSet"],
            "mongo_repo": ".",
            "evergreen_config": FIXTURE.repo_root_file_path("config.yml"),
            "n": 2,
        }
        cmd1 = client._evergreen_patch_compile_cmd(1)
        cmd2 = client._evergreen_patch_compile_cmd(2)
        self.assertEqual(cmd1, expected1)
        self.assertEqual(cmd2, expected2)

    def test_result_urls(self):
        """MultiEvergreen: build result urls"""
        # pylint: disable=line-too-long
        expected = [
            {
                "ID": "586582573ff1224524001e99",
                "build_variant_ids": [
                    "sys_perf_linux_1_node_replSet_651bc712c372e619513f1cc9564a38bf5b665237_16_12_29_21_39_27",
                    "sys_perf_linux_standalone_651bc712c372e619513f1cc9564a38bf5b665237_16_12_29_21_39_27",
                ],
                "result_urls": [
                    "https://evergreen.mongodb.com/plugin/json/task/sys_perf_linux_1_node_replSet_core_workloads_MMAPv1_651bc712c372e619513f1cc9564a38bf5b665237_16_12_29_21_39_27/perf/",
                    "https://evergreen.mongodb.com/plugin/json/task/sys_perf_linux_1_node_replSet_core_workloads_WT_651bc712c372e619513f1cc9564a38bf5b665237_16_12_29_21_39_27/perf/",
                    "https://evergreen.mongodb.com/plugin/json/task/sys_perf_linux_standalone_core_workloads_MMAPv1_651bc712c372e619513f1cc9564a38bf5b665237_16_12_29_21_39_27/perf/",
                    "https://evergreen.mongodb.com/plugin/json/task/sys_perf_linux_standalone_core_workloads_WT_651bc712c372e619513f1cc9564a38bf5b665237_16_12_29_21_39_27/perf/",
                ],
                "task_ids": [
                    "sys_perf_linux_1_node_replSet_core_workloads_MMAPv1_651bc712c372e619513f1cc9564a38bf5b665237_16_12_29_21_39_27",
                    "sys_perf_linux_1_node_replSet_core_workloads_WT_651bc712c372e619513f1cc9564a38bf5b665237_16_12_29_21_39_27",
                    "sys_perf_linux_standalone_core_workloads_MMAPv1_651bc712c372e619513f1cc9564a38bf5b665237_16_12_29_21_39_27",
                    "sys_perf_linux_standalone_core_workloads_WT_651bc712c372e619513f1cc9564a38bf5b665237_16_12_29_21_39_27",
                ],
            },
            {
                "ID": "586582553ff1224524001e96",
                "build_variant_ids": [
                    "sys_perf_linux_standalone_651bc712c372e619513f1cc9564a38bf5b665237_16_12_29_21_39_24",
                    "sys_perf_linux_1_node_replSet_651bc712c372e619513f1cc9564a38bf5b665237_16_12_29_21_39_24",
                ],
                "result_urls": [
                    "https://evergreen.mongodb.com/plugin/json/task/sys_perf_linux_standalone_core_workloads_MMAPv1_651bc712c372e619513f1cc9564a38bf5b665237_16_12_29_21_39_24/perf/",
                    "https://evergreen.mongodb.com/plugin/json/task/sys_perf_linux_standalone_core_workloads_WT_651bc712c372e619513f1cc9564a38bf5b665237_16_12_29_21_39_24/perf/",
                    "https://evergreen.mongodb.com/plugin/json/task/sys_perf_linux_1_node_replSet_core_workloads_MMAPv1_651bc712c372e619513f1cc9564a38bf5b665237_16_12_29_21_39_24/perf/",
                    "https://evergreen.mongodb.com/plugin/json/task/sys_perf_linux_1_node_replSet_core_workloads_WT_651bc712c372e619513f1cc9564a38bf5b665237_16_12_29_21_39_24/perf/",
                ],
                "task_ids": [
                    "sys_perf_linux_standalone_core_workloads_MMAPv1_651bc712c372e619513f1cc9564a38bf5b665237_16_12_29_21_39_24",
                    "sys_perf_linux_standalone_core_workloads_WT_651bc712c372e619513f1cc9564a38bf5b665237_16_12_29_21_39_24",
                    "sys_perf_linux_1_node_replSet_core_workloads_MMAPv1_651bc712c372e619513f1cc9564a38bf5b665237_16_12_29_21_39_24",
                    "sys_perf_linux_1_node_replSet_core_workloads_WT_651bc712c372e619513f1cc9564a38bf5b665237_16_12_29_21_39_24",
                ],
            },
        ]
        args = ["--description", "PERF-814 Unit test, please ignore", "-n", "2"]
        client = MultiEvergreen(args)
        # Needed to initialize evergreen REST client
        client.config["evergreen_config"] = FIXTURE.repo_root_file_path("config.yml")
        client.parse_options()
        client.builds = [{"ID": "586582573ff1224524001e99"}, {"ID": "586582553ff1224524001e96"}]
        client.config["result_urls"] = True
        client.evergreen_result_urls()
        self.assertEqual(client.builds, expected)

    def test_deserialize_serialize(self):
        """MultiEvergreen: Do a no-op deserialize & serialize of the yaml file."""
        expected_file = FIXTURE.fixture_file_path("multi_patch_builds.yml.noop.ok")
        input_file = FIXTURE.fixture_file_path("multi_patch_builds.yml")
        args = ["--continue", input_file]
        client = MultiEvergreen(args)
        client.config["evergreen_config"] = FIXTURE.repo_root_file_path("config.yml")
        client.parse_options()
        # Note that here serialize() overwrites input_file with the identical contents
        client.execute()
        with open(expected_file) as exp_file_handle:
            expected_yaml = yaml.load(exp_file_handle)
        with open(input_file) as obs_file_handle:
            observed_yaml = yaml.load(obs_file_handle)
        self.assertEqual(observed_yaml, expected_yaml)


if __name__ == "__main__":
    unittest.main()
