# -*- coding: UTF-8 -*-
"""Tests for dsi/common/config.py"""

import os
import unittest

import yaml
from six.moves import range
from six.moves import zip

import dsi.common.whereami as whereami
from dsi.common import config
from dsi.common.config import ConfigDict
from test_lib.fixture_files import FixtureFiles, load_config_dict
from test_lib.io_utils import in_dir

FIXTURE_FILES = FixtureFiles()


def dirmarker(into):
    """chdir into `into` (relatie to __file__) and return a function
    that when called will chdir back to where you were before.

    Example usage:

        marker = dirmarker('subdir')
        process_file('foo.txt') # inside subdir
        marker()

    """
    old_dir = os.getcwd()
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), into)
    os.chdir(path)
    return lambda: os.chdir(old_dir)


class InvalidConfigDictTestCase(unittest.TestCase):
    """Test that we're as picky as we claim to be with config keys and values"""

    def test_load_yaml_invalid_keys(self):
        """can't even get bad keys from yaml"""
        with in_dir(FIXTURE_FILES.fixture_file_path("invalid-config")):
            with self.assertRaises(config.InvalidConfigurationException):
                ConfigDict("mongodb_setup").load()

    def test_set_invalid_key(self):
        """can't use conf[key] = X with key invalid"""
        with in_dir(FIXTURE_FILES.fixture_file_path("nested-config")):
            conf = load_config_dict("mongodb_setup")
            self.assertEqual(
                conf["mongodb_setup"]["this"]["is"]["quite"]["deeply"]["nested"], "okay"
            )
            conf["mongodb_setup"]["out"] = {}
            conf["mongodb_setup"]["out"]["safe-key"] = "💃"
            self.assertEqual(conf["mongodb_setup"]["out"]["safe-key"], "💃")

    def causes_exception(self, subdict):
        """
        Helper method - assert we get an exception when `subdict` is inserted into an out config
        """
        with in_dir(FIXTURE_FILES.fixture_file_path("nested-config")):
            conf = load_config_dict("mongodb_setup")
            with self.assertRaises(config.InvalidConfigurationException):
                conf["mongodb_setup"]["out"] = {"okay": [subdict]}

    def test_assigns_invalid_space_key(self):
        """spaces not allowed"""
        self.causes_exception(
            {
                "this has a space": "and shouldn't work (because it has a back problem not because it's lazy and entitled"
            }
        )

    def test_assigns_invalid_numeric_key(self):
        """number-only not allowed"""
        self.causes_exception({"1": "woah dude a numeric-only key. get a job, you hippie."})

    def test_assigns_exclamation_point_key(self):
        """! not allowed"""
        self.causes_exception({"hello!": "is it me you're looking for?"})

    def test_assigns_dot_key(self):
        """dots not allowed"""
        self.causes_exception({"so...uh...": "dot dot dot"})

    def test_assigns_slashy_key(self):
        """slashes not allowed"""
        self.causes_exception({"data/logs": "logging kills trees"})

    def test_assigns_invalid_nested_dict_multiple_errors(self):
        """assign invalid key from a nested dict with multiple errors"""
        with in_dir(FIXTURE_FILES.fixture_file_path("nested-config")):
            conf = load_config_dict("mongodb_setup")
            with self.assertRaises(config.InvalidConfigurationException) as context:
                conf["mongodb_setup"]["out"] = {
                    "okay": [
                        {
                            "okay": "this is fine",
                            "not okay": "you're killing me, bro!",
                            "seriously, just stop now": "but all the cool kids are doing it",
                        }
                    ]
                }
            # we're non-normative on what the actual message is, but we
            # do care that all the errored keys are there
            self.assertRegex(str(context.exception), r"not okay")
            self.assertRegex(str(context.exception), r"seriously")

    def causes_id_exception(self, subdict):
        """
        Helper method - assert we get an exception when subdict is inserted into a config.
        Note: These tests explicitly test `validate_id` when called from `_yaml_load` (as opposed to
        when it's called from `assert_valid_ids`).
        """
        with in_dir(FIXTURE_FILES.fixture_file_path("invalid-ids")):
            conf = load_config_dict("mongodb_setup")
            with self.assertRaises(config.InvalidConfigurationException):
                conf["mongodb_setup"]["test"] = {"okay": [subdict]}

    def test_id_is_reserved_word(self):
        """
        Cannot use a reserved word (enumerated in `config.py`) as an id.
        """
        self.causes_id_exception({"id": "pre_task"})

    def test_id_matches_reserved_pattern(self):
        """
        Cannot use a word matching the pattern /on_.*/ as an id.
        """
        self.causes_id_exception({"id": "on_load"})

    def test_id_value_type_incorrect(self):
        """
        Cannot have an id value that is not a scalar.
        """
        self.causes_id_exception({"id": {"wrong": "format"}})

    def test_duplicate_id_same_level(self):
        """
        Cannot have duplicate ids on the same level.
        """
        self.causes_id_exception(
            {"stuff": [{"id": "myname", "hey": "greetings"}, {"id": "myname", "bye": "see ya"}]}
        )

    def test_nested_duplicate_ids(self):
        """
        Ids must be globally unique in config files.
        """
        self.causes_id_exception({"id": "myname", "test": {"id": "myname"}})

    def test_variable_reference_is_invalid_id(self):
        """
        Variable references cannot evaluate to duplicate ids.
        """
        with in_dir(FIXTURE_FILES.fixture_file_path("invalid-ids")):
            with self.assertRaises(config.InvalidConfigurationException):
                conf = ConfigDict("mongodb_setup")
                conf.load()

    def test_variable_reference_contains_invalid_id(self):
        """
        Variable references cannot evaluate to blocks containing duplicate ids.
        """
        with in_dir(FIXTURE_FILES.fixture_file_path("nested-invalid-ids")):
            with self.assertRaises(config.InvalidConfigurationException):
                conf = ConfigDict("mongodb_setup")
                conf.load()

    def test_find_nested_config_dicts(self):
        """
        We check for duplicate ids in lists of lists correctly.
        """
        with in_dir(FIXTURE_FILES.fixture_file_path("invalid-ids-in-lists")):
            with self.assertRaises(config.InvalidConfigurationException):
                conf = ConfigDict("mongodb_setup")
                conf.load()


class ConfigDictTestCase(unittest.TestCase):
    """Unit tests for ConfigDict library."""

    def setUp(self):
        """Init a ConfigDict object and load the configuration files from docs/config-specs/"""
        self.conf = ConfigDict("mongodb_setup", whereami.dsi_repo_path("docs", "config-specs"))
        self.conf.load()
        self.assertEqual(self.conf.module, "mongodb_setup")

    def test_load_new(self):
        """Test loading ConfigDict with old naming convention .yml files"""
        test_conf = ConfigDict(
            "bootstrap", whereami.dsi_repo_path("dsi", "tests", "test_config_files", "new_format")
        )
        test_conf.load()
        self.assertFalse("cluster_type" in test_conf.raw["bootstrap"])
        self.assertTrue("infrastructure_provisioning" in test_conf.raw["bootstrap"])
        self.assertFalse("cluster_type" in test_conf.defaults["bootstrap"])
        self.assertTrue("infrastructure_provisioning" in test_conf.defaults["bootstrap"])

    def test_none_valued_keys(self):
        config_dict = self.conf
        self.assertEqual(config_dict["runtime"]["overridden_none"], "hey there")
        self.assertEqual(config_dict["runtime"]["override_with_none"], None)
        self.assertEqual(config_dict["runtime"]["overridden_dict"], None)
        self.assertEqual(config_dict["runtime"]["overridden_list"], None)
        with self.assertRaises(KeyError):
            config_dict["runtime"]["nonexistant"]  # pylint: disable=pointless-statement

    def test_traverse_entire_dict(self):
        """Traverse entire dict (also tests that the structure of docs/config-specs/ files are ok)"""
        # We actually could compare the result to a constant megadict here, but maintaining that
        # would quickly become tedious. In practice, there's huge value just knowing we can traverse
        # the entire structure without errors.
        str(self.conf)

    @unittest.skip("dict(instance_of_ConfigDict) does not work")
    def test_cast_as_dict(self):
        """It is possible to cast a ConfigDict to a dict"""
        # TODO: this doesn't actually work. Seems like a limitation of python when sub-classing
        # native type like dict: http://stackoverflow.com/questions/18317905/overloaded-iter-is-bypassed-when-deriving-from-dict
        complete_dict = dict(self.conf)
        sub_dict = dict(self.conf["workload_setup"]["tasks"][0]["on_workload_client"])
        self.assertEqual(
            complete_dict["workload_setup"]["tasks"][0]["on_workload_client"]["retrieve_files"][0],
            {"source": "http://url1", "target": "file"},
        )
        self.assertEqual(
            sub_dict["retrieve_files"][0],
            {"source": "remote_file_path", "target": "local_file_path"},
        )

    def test_convert_to_dict(self):
        """It is possible to convert a ConfigDict to a dict with self.as_dict()"""
        complete_dict = self.conf.as_dict()
        sub_dict = self.conf["workload_setup"]["ycsb"][0]["on_workload_client"].as_dict()
        self.assertEqual(
            complete_dict["workload_setup"]["ycsb"][0]["on_workload_client"]["retrieve_files"][0],
            {"source": "remote_file_path", "target": "local_file_path"},
        )
        self.assertEqual(
            sub_dict["retrieve_files"][0],
            {"source": "remote_file_path", "target": "local_file_path"},
        )

    def test_basic_checks(self):
        """Basic checks"""
        self.assert_equal_dicts(
            self.conf["workload_setup"]["ycsb"][0]["on_workload_client"]["retrieve_files"][0],
            {"source": "remote_file_path", "target": "local_file_path"},
        )
        expected_result = [{"source": "remote_file_path", "target": "local_file_path"}]
        actual_result = self.conf["workload_setup"]["ycsb"][0]["on_workload_client"][
            "retrieve_files"
        ]
        self.assertEqual(len(actual_result), len(expected_result))
        for actual, expected in zip(actual_result, expected_result):
            self.assert_equal_dicts(actual, expected)
        self.assert_equal_dicts(
            self.conf["infrastructure_provisioning"]["out"]["mongos"][2],
            {"public_ip": "53.1.1.102", "private_ip": "10.2.1.102"},
        )
        self.assertEqual(
            self.conf["infrastructure_provisioning"]["out"]["workload_client"][0]["public_ip"],
            "53.1.1.101",
        )
        self.assertEqual(
            type(
                self.conf["infrastructure_provisioning"]["out"]["workload_client"][0]["public_ip"]
            ),
            type(""),
        )

    def test_overrides(self):
        """Test value from overrides.yml"""
        self.assertEqual(
            self.conf["infrastructure_provisioning"]["tfvars"]["configsvr_instance_type"],
            "t1.micro",
        )
        self.assertEqual(
            self.conf["infrastructure_provisioning"]["tfvars"].as_dict(),
            {
                "cluster_name": "shard",
                "mongos_instance_type": "c3.8xlarge",
                "availability_zone": "us-west-2a",
                "workload_instance_count": 1,
                "region": "us-west-2",
                "image": "amazon2",
                "mongod_instance_count": 9,
                "configsvr_instance_count": 3,
                "mongos_instance_count": 3,
                "ssh_key_file": "~/.ssh/linustorvalds.pem",
                "ssh_user": "ec2-user",
                "mongod_instance_type": "c3.8xlarge",
                "ssh_key_name": "linus.torvalds",
                "workload_instance_type": "c3.8xlarge",
                "tags": {
                    "Project": "sys-perf",
                    "owner": "linus.torvalds@10gen.com",
                    "Variant": "Linux 3-shard cluster",
                    "expire-on-delta": 2,
                },
                "configsvr_instance_type": "t1.micro",
                "expire-on-delta": 24,
            },
        )

    def test_defaults(self):
        """Test value from defaults.yml"""
        self.assertEqual(self.conf["mongodb_setup"]["mongod_config_file"]["net"]["port"], 27017)
        self.assertEqual(
            self.conf["mongodb_setup"]["mongod_config_file"]["processManagement"]["fork"], True
        )

    def test_copy(self):
        """Copy value into new python variable"""
        out = self.conf["infrastructure_provisioning"]["out"]
        self.conf.raw["infrastructure_provisioning"]["out"]["workload_client"][0][
            "private_ip"
        ] = "foo"
        out.raw["workload_client"][0]["public_ip"] = "bar"
        self.assertTrue(isinstance(out, ConfigDict))
        self.assert_equal_lists(
            self.conf.raw["infrastructure_provisioning"]["out"]["workload_client"],
            [{"public_ip": "bar", "private_ip": "foo"}],
        )
        self.assert_equal_lists(
            self.conf.root["infrastructure_provisioning"]["out"]["workload_client"],
            [{"public_ip": "bar", "private_ip": "foo"}],
        )
        self.assert_equal_lists(
            out.raw["workload_client"], [{"public_ip": "bar", "private_ip": "foo"}]
        )
        self.assert_equal_lists(
            out.root["infrastructure_provisioning"]["out"]["workload_client"],
            [{"public_ip": "bar", "private_ip": "foo"}],
        )
        self.assert_equal_dicts(out.overrides, {})
        self.assertEqual(out["workload_client"][0]["public_ip"], "bar")

    def test_items(self):
        actual = {k for k, v in self.conf["bootstrap"].items()}
        expect = {
            "production",
            "analysis",
            "workload_setup",
            "terraform",
            "infrastructure_provisioning",
            "overrides",
            "storageEngine",
            "test_control",
            "platform",
            "mongodb_setup",
        }

        self.assertEqual(actual, expect)

    def test_variable_references(self):
        """Test ${variable.references}"""
        self.assertEqual(
            self.conf["mongodb_setup"]["topology"][0]["mongos"][0]["private_ip"], "10.2.1.100"
        )
        self.assertEqual(
            self.conf["mongodb_setup"]["meta"]["hosts"],
            "10.2.1.100:27017,10.2.1.101:27017,10.2.1.102:27017",
        )

        # reference to reference
        self.assertEqual(self.conf["mongodb_setup"]["meta"]["hostname"], "10.2.1.100")

        # recursive reference ${a.${foo}.c} where "foo: b"
        value = self.conf["test_control"]["run"][0]["workload_config"]["tests"]["default"][2][
            "insert_vector"
        ]["thread_levels"]
        expected = [1, 8, 16]
        self.assertEqual(value, expected)

    def test_variable_reference_in_list(self):
        """Test ${variable.references} in a list"""
        self.assertEqual(self.conf["mongodb_setup"]["validate"]["primaries"][0], "10.2.1.1:27017")

    def test_variable_reference_value_error(self):
        """Test ${variable.references} that point to nonexisting value PERF-1705"""
        # PERF-1705 happened when infrastructure_provisioning.out doesn't exist and variable
        # references point to it.
        del self.conf.raw["infrastructure_provisioning"]["out"]

        # ConfigDict is late binding
        # assert_valid_ids() (used in load()) should not raise for such variable references.
        self.conf.assert_valid_ids()

        # Otoh actively accessing a field with such a variable reference must raise
        with self.assertRaises(ValueError):
            _ = self.conf["mongodb_setup"]["meta"]["mongodb_url"]

        # As must other methods where user causes entire ConfigDict to be traversed
        with self.assertRaises(ValueError):
            _ = self.conf.as_dict()
        with self.assertRaises(ValueError):
            _ = str(self.conf)

    def test_per_node_mongod_config(self):
        """Test magic per_node_mongod_config() (merging the common mongod_config_file with per node config_file)"""
        mycluster = self.conf["mongodb_setup"]["topology"][0]
        mongod = mycluster["shard"][2]["mongod"][0]
        self.assert_equal_dicts(
            mycluster["shard"][0]["mongod"][0]["config_file"],
            {
                "replication": {"replSetName": "override-rs"},
                "systemLog": {"path": "data/logs/mongod.log", "destination": "file"},
                "setParameter": {"enableTestCommands": True, "foo": True},
                "net": {"port": 27017, "bindIp": "0.0.0.0"},
                "processManagement": {"fork": True},
                "storage": {"engine": "wiredTiger", "dbPath": "data/dbs"},
            },
        )
        self.assert_equal_dicts(
            mycluster["shard"][2]["mongod"][0]["config_file"],
            {
                "replication": {"replSetName": "override-rs"},
                "systemLog": {"path": "data/logs/mongod.log", "destination": "file"},
                "setParameter": {"enableTestCommands": True, "foo": True},
                "net": {"port": 27017, "bindIp": "0.0.0.0"},
                "processManagement": {"fork": True},
                "storage": {"engine": "inMemory", "dbPath": "data/dbs"},
            },
        )
        self.assert_equal_dicts(
            mycluster["shard"][2]["mongod"][0]["config_file"].overrides,
            {"storage": {"engine": "inMemory"}},
        )
        self.assertEqual(
            mycluster["shard"][2]["mongod"][0]["config_file"]["storage"]["engine"], "inMemory"
        )
        self.assertEqual(mycluster["shard"][2]["mongod"][0]["config_file"]["net"]["port"], 27017)
        self.assertEqual(
            mycluster["shard"][2]["mongod"][0]["config_file"]["net"]["bindIp"], "0.0.0.0"
        )
        self.assertEqual(
            mycluster["shard"][2]["mongod"][0]["config_file"]["processManagement"]["fork"], True
        )
        self.assertEqual(
            mongod.raw,
            {
                "public_ip": "${infrastructure_provisioning.out.mongod.6.public_ip}",
                "mongodb_binary_archive": "${mongodb_setup.mongodb_binary_archive}",
                "config_file": {"storage": {"engine": "inMemory"}},
                "private_ip": "${infrastructure_provisioning.out.mongod.6.private_ip}",
            },
        )
        # Standalone node
        self.assert_equal_dicts(
            self.conf["mongodb_setup"]["topology"][2]["config_file"],
            {
                "replication": {"replSetName": "override-rs"},
                "systemLog": {"path": "data/logs/mongod.log", "destination": "file"},
                "setParameter": {"enableTestCommands": True, "foo": True},
                "net": {"port": 27017, "bindIp": "0.0.0.0"},
                "processManagement": {"fork": True},
                "storage": {"engine": "wiredTiger", "dbPath": "data/dbs"},
            },
        )
        # self.keys() should return a 'config_file' key
        self.assertTrue("config_file" in mycluster["shard"][0]["mongod"][0].keys())
        self.assertTrue("config_file" in mycluster["shard"][2]["mongod"][0].keys())
        self.assertTrue("config_file" in self.conf["mongodb_setup"]["topology"][2].keys())
        self.assertFalse("config_file" in self.conf["mongodb_setup"]["topology"][0].keys())

    def test_replset_rs_conf(self):
        """Test magic rs_conf for a replset"""
        mycluster = self.conf["mongodb_setup"]["topology"][0]
        rs_conf = mycluster["shard"][2]["rs_conf"]
        self.assertEqual(rs_conf["protocolVersion"], 1)
        myreplset = self.conf["mongodb_setup"]["topology"][1]
        rs_conf = myreplset["rs_conf"]
        self.assertEqual(rs_conf["settings"]["chainingAllowed"], False)
        self.assertEqual(rs_conf["protocolVersion"], 1)

        # conf.keys() should return a 'config_file' key for replsets, not otherwise
        self.assertTrue("rs_conf" in mycluster["shard"][0].keys())
        self.assertTrue("rs_conf" in mycluster["shard"][2].keys())
        self.assertTrue("rs_conf" in myreplset.keys())
        self.assertFalse("rs_conf" in mycluster.keys())
        self.assertFalse("rs_conf" in self.conf["mongodb_setup"]["topology"][2].keys())
        self.assertFalse("rs_conf" in self.conf["infrastructure_provisioning"].keys())

    def test_set_some_values(self):
        """Set some values and write out file"""
        self.conf["mongodb_setup"]["out"] = {"foo": "bar"}
        # Read the value multiple times, because once upon a time that didn't work (believe it or not)
        self.assert_equal_dicts(self.conf["mongodb_setup"]["out"], {"foo": "bar"})
        self.assert_equal_dicts(self.conf["mongodb_setup"]["out"], {"foo": "bar"})
        self.assert_equal_dicts(self.conf["mongodb_setup"]["out"], {"foo": "bar"})
        self.conf["mongodb_setup"]["out"]["zoo"] = "zar"
        self.assert_equal_dicts(self.conf["mongodb_setup"]["out"], {"foo": "bar", "zoo": "zar"})
        with self.assertRaises(KeyError):
            self.conf["foo"] = "bar"
        # Write the out file only if it doesn't already exist, and delete it when done
        file_name = os.path.join(
            whereami.dsi_repo_path("docs", "config-specs"), "mongodb_setup.out.yml"
        )
        if os.path.exists(file_name):
            self.fail(
                "Cannot test writing docs/config-specs/mongodb_setup.out.yml file, file already exists."
            )
        else:
            self.conf.save()
            file_handle = open(file_name)
            saved_out_file = yaml.safe_load(file_handle)
            file_handle.close()
            self.assert_equal_dicts({"out": self.conf["mongodb_setup"]["out"]}, saved_out_file)
            os.remove(file_name)

    def test_iterators(self):
        """Test that iterators .keys() and .values() work"""
        mycluster = self.conf["mongodb_setup"]["topology"][0]
        self.assertEqual(
            set(self.conf.keys()),
            {
                "test_control",
                "workload_setup",
                "runtime_secret",
                "bootstrap",
                "mongodb_setup",
                "analysis",
                "infrastructure_provisioning",
                "runtime",
            },
        )

        tfvars_dict = dict(
            zip(
                self.conf["infrastructure_provisioning"]["tfvars"].keys(),
                self.conf["infrastructure_provisioning"]["tfvars"].values(),
            )
        )

        self.assert_equal_dicts(
            tfvars_dict,
            {
                "cluster_name": "shard",
                "mongos_instance_type": "c3.8xlarge",
                "availability_zone": "us-west-2a",
                "workload_instance_count": 1,
                "image": "amazon2",
                "region": "us-west-2",
                "mongod_instance_count": 9,
                "configsvr_instance_count": 3,
                "mongos_instance_count": 3,
                "ssh_key_file": "~/.ssh/linustorvalds.pem",
                "ssh_user": "ec2-user",
                "mongod_instance_type": "c3.8xlarge",
                "ssh_key_name": "linus.torvalds",
                "workload_instance_type": "c3.8xlarge",
                "tags": {
                    "Project": "sys-perf",
                    "owner": "linus.torvalds@10gen.com",
                    "Variant": "Linux 3-shard cluster",
                    "expire-on-delta": 2,
                },
                "configsvr_instance_type": "t1.micro",
                "expire-on-delta": 24,
            },
        )

        # Order doesn't matter, but this can't be a set because dicts aren't hashable.
        expect = [
            "53.1.1.7",
            "https://fastdl.mongodb.org/linux/mongodb-linux-x86_64-amazon-3.4.6.tgz",
            "10.2.1.7",
        ]
        actual = mycluster["shard"][2]["mongod"][0].values()
        # There is a 4th item in the list that's not in expect because we can't easily assert on its value.
        self.assertEqual(4, len(actual))
        for val in expect:
            self.assertTrue(val in actual, f"Val {val} not present")

    def test_lookup_path(self):
        """check that the lookup_path works as expected."""

        conf = self.conf["infrastructure_provisioning"]["out"]

        self.assertIsInstance(conf.lookup_path("mongod"), list)
        self.assertIsInstance(conf.lookup_path("mongod.0"), ConfigDict)
        self.assertIsInstance(conf.lookup_path("mongod.0.public_ip"), str)

        # hard coded but quick and easy
        mongod = ["53.1.1.{}".format(i) for i in range(1, 10)]
        mongos = ["53.1.1.{}".format(i) for i in range(100, 102)]
        configsvr = ["53.1.1.{}".format(i) for i in range(51, 54)]
        workload_client = ["53.1.1.101"]

        self.assertEqual(conf.lookup_path("mongod.0.public_ip"), mongod[0])

        self.assertEqual(conf.lookup_path("mongod.1.public_ip"), mongod[1])
        self.assertEqual(conf.lookup_path("mongod.4.public_ip"), mongod[4])

        self.assertEqual(conf.lookup_path("mongos.0.public_ip"), mongos[0])
        self.assertEqual(conf.lookup_path("configsvr.0.public_ip"), configsvr[0])
        self.assertEqual(conf.lookup_path("workload_client.0.public_ip"), workload_client[0])

        # document that this is the current behavior
        self.assertEqual(conf.lookup_path("mongod.-1.public_ip"), mongod[-1])

    def test_lookup_path_ex(self):
        """check that lookup_path throws exceptions for the correct portion of the pathspec."""

        conf = self.conf["infrastructure_provisioning"]["out"]
        self.assertRaisesRegex(
            KeyError,
            "ConfigDict: Key not found: MONGOD in path \\['MONGOD'\\]",
            conf.lookup_path,
            "MONGOD",
        )
        self.assertRaisesRegex(
            KeyError,
            "ConfigDict: Key not found: MONGOD in path \\['MONGOD', 50\\]",
            conf.lookup_path,
            "MONGOD.50",
        )
        self.assertRaisesRegex(
            KeyError,
            "ConfigDict: list index out of range: mongod.50 in path \\['mongod', 50\\]",
            conf.lookup_path,
            "mongod.50",
        )
        self.assertRaisesRegex(
            KeyError,
            "ConfigDict: Key not found: mongod.50e-1 in path \\['mongod', '50e-1'\\]",
            conf.lookup_path,
            "mongod.50e-1",
        )
        self.assertRaisesRegex(
            KeyError,
            "ConfigDict: list index out of range: mongod.50 in path \\['mongod', 50, 'public_ip'\\]",
            conf.lookup_path,
            "mongod.50.public_ip",
        )
        self.assertRaisesRegex(
            KeyError,
            "ConfigDict: Key not found: mongod.0.0 in path \\['mongod', 0, 0\\]",
            conf.lookup_path,
            "mongod.0.0",
        )
        self.assertRaisesRegex(
            KeyError,
            "ConfigDict: list index out of range: mongod.50 in path \\['mongod', 50, 'public_ip', 0\\]",
            conf.lookup_path,
            "mongod.50.public_ip.0",
        )

    # Helpers
    def assert_equal_dicts(self, dict1, dict2):
        """Compare 2 dicts element by element for equal values."""
        dict1keys = list(dict1.keys())
        dict2keys = list(dict2.keys())
        self.assertEqual(len(dict1keys), len(dict2keys))
        self.assertEqual(set(dict1keys), set(dict2keys))
        for dict1key in dict1keys:
            # Pop the corresponding key from dict2, note that they won't be in the same order.
            dict2key = dict2keys.pop(dict2keys.index(dict1key))
            self.assertEqual(
                dict1key,
                dict2key,
                "assert_equal_dicts failed: mismatch in keys: "
                + str(dict1key)
                + "!="
                + str(dict2key),
            )
            if isinstance(dict1[dict1key], dict):
                self.assert_equal_dicts(dict1[dict1key], dict2[dict2key])
            elif isinstance(dict1[dict1key], list):
                self.assert_equal_lists(dict1[dict1key], dict2[dict2key])
            else:
                self.assertEqual(
                    dict1[dict1key],
                    dict2[dict2key],
                    "assert_equal_dicts failed: mismatch in values.",
                )
        self.assertEqual(len(dict2keys), 0)

    def assert_equal_lists(self, list1, list2):
        """Compare 2 lists element by element for equal values."""
        self.assertEqual(len(list1), len(list2))
        for list1value in list1:
            list2value = list2.pop(0)
            if isinstance(list1value, dict):
                self.assert_equal_dicts(list1value, list2value)
            elif isinstance(list1value, list):
                self.assert_equal_lists(list1value, list2value)
            else:
                self.assertEqual(list1value, list2value, "{} != {}".format(list1, list2))
        self.assertEqual(len(list2), 0)


if __name__ == "__main__":
    unittest.main()
