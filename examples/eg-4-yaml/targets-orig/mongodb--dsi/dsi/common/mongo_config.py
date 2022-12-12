"""
Various classes that parse ConfigDicts and represent them to clusters.
"""


import json
import os

import six
import yaml

from dsi.common import mongodb_setup_helpers
from dsi.common.config import copy_obj
from dsi.common.host_utils import ssh_user_and_key_file
from dsi.common.models.host_info import HostInfo

DEFAULT_JOURNAL_DIR = "/media/ephemeral1/journal"
DEFAULT_CSRS_NAME = "configSvrRS"


# pylint: disable=too-many-instance-attributes
class MongoConfig:
    """
    Class representing the configuration of a single mongod or mongos.
    """

    def __init__(self, root_config, topology, is_mongos=False):
        """
        :param root_config: Root ConfigDict.
        :param topology: ConfigDict representing this node's location in the topology.
        :param is_mongos: Whether this configuration is for a mongos instance or not.
        """
        mongodb_setup = root_config["mongodb_setup"]

        # Get the mongo_dir from the topology if set, otherwise from the mongo_dir.
        # It now must come from configuration.
        self.bin_dir = os.path.join(
            topology.get("mongo_dir", mongodb_setup.get("mongo_dir")), "bin"
        )

        self.clean_logs = topology.get("clean_logs", mongodb_setup.get("clean_logs", True))
        self.clean_db_dir = topology.get(
            "clean_db_dir", (not is_mongos) and mongodb_setup.get("clean_db_dir", True)
        )

        self.use_journal_mnt = topology.get("use_journal_mnt", not is_mongos)
        config_file = copy_obj(topology.get("config_file", {}))
        self.logdir = os.path.dirname(config_file["systemLog"]["path"])
        self.log_path = config_file["systemLog"]["path"]
        self.contents = yaml.dump(config_file, default_flow_style=False)

        self.mongo_program = "mongos" if is_mongos else "mongod"

        if is_mongos:
            self.dbdir = None
        else:
            self.dbdir = config_file["storage"]["dbPath"]

        self.numactl_prefix = root_config["infrastructure_provisioning"].get("numactl_prefix", "")

        # The numactl_prefix is used in shell scripts directly invoked from yaml configs as a shell
        # variable, so it has to be a string. Ideally we want the configuration for numactl to
        # already be a list of commandline arguments.
        if isinstance(self.numactl_prefix, six.string_types):
            self.numactl_prefix = self.numactl_prefix.split(" ")

        self.shutdown_options = json.dumps(copy_obj(mongodb_setup["shutdown_options"]))

        self.journal_dir = root_config["mongodb_setup"].get("journal_dir", DEFAULT_JOURNAL_DIR)

    def get_setup_command_args(self, restart_clean_db_dir, restart_clean_logs):
        """
        Returns the arguments needed to set up a host.
        :param restart_clean_db_dir: Should we clean db dir on restart. If not specified, uses value
        from ConfigDict.
        :param restart_clean_logs: Should we clean logs and diagnostic data. If not specified,
        uses value from ConfigDict.
        These values can be overridden with ConfigDict values because they may be set in
        certain test_control files.
        """
        if restart_clean_db_dir is not None:
            clean_db_dir = restart_clean_db_dir
        else:
            clean_db_dir = self.clean_db_dir
        clean_logs = restart_clean_logs if restart_clean_logs is not None else self.clean_logs

        # NB: self.dbdir is None when self.is_mongos is True
        return {
            "clean_db_dir": clean_db_dir,
            "clean_logs": clean_logs,
            "dbdir": self.dbdir,
            "journal_dir": self.journal_dir,
            "logdir": os.path.dirname(self.log_path),
            "is_mongos": self.mongo_program == "mongos",
            "use_journal_mnt": self.use_journal_mnt,
        }

    def get_config(self, preserve_repl_auth=True):
        """
        Returns the current config string,
        optionally removing authentication fields.
        :param preserve_repl_auth False to remove ReplSet auth keys.
        """
        if preserve_repl_auth:
            return self.contents

        contents = self.contents
        config = yaml.load(contents)
        if "security" in config:
            if "keyFile" in config["security"]:
                del config["security"]["keyFile"]
                contents = yaml.dump(config, default_flow_style=False)
            if "clusterAuthMode" in config["security"]:
                del config["security"]["clusterAuthMode"]
                contents = yaml.dump(config, default_flow_style=False)

        return contents


class NetConfig:
    """
    Class representing the network configuration for a single cluster node.
    """

    def __init__(self, topology, root_config):
        """
        :param topology: The topology ConfigDict for this node.
        :param root_config: The root ConfigDict.
        """
        self.public_ip = topology["public_ip"]
        self.private_ip = topology.get("private_ip", self.public_ip)
        self.tls_settings = mongodb_setup_helpers.mongodb_tls_settings(topology["config_file"])
        config_file = copy_obj(topology.get("config_file", {}))
        self.port = config_file["net"]["port"]
        (self.ssh_user, self.ssh_key_file) = ssh_user_and_key_file(root_config)
        self.spawn_using = root_config["test_control"].get("spawn_using", "ssh")

    def compute_host_info(self):
        """Create host wrapper to run commands."""
        return HostInfo(
            public_ip=self.public_ip,
            private_ip=self.private_ip,
            ssh_user=self.ssh_user,
            ssh_key_file=self.ssh_key_file,
        )


class NodeTopologyConfig:
    """ Class representing a leaf node of the topology tree. """

    def __init__(self, topology, root_config, delay_graph, is_mongos=False):
        """
        :param root_config: Root ConfigDict.
        :param topology: ConfigDict representing this node's location in the topology.
        :param delay_graph: The DelayGraph object representing this cluster's delays.
        """
        self.mongo_config = MongoConfig(root_config, topology, is_mongos)
        self.net_config = NetConfig(topology, root_config)
        self.delay_node = delay_graph.get_node(self.net_config.compute_host_info().private_ip)
        self.auth_settings = mongodb_setup_helpers.mongodb_auth_settings(root_config)
        self.use_tls = mongodb_setup_helpers.mongodb_tls_configured(
            root_config["mongodb_setup"]["mongod_config_file"]
        )


class ReplTopologyConfig:
    """
    Class representing a ReplSet's topology configuration.
    """

    replsets = 0

    def __init__(self, topology, root_config, delay_graph):
        """
        :param root_config: Root ConfigDict.
        :param topology: ConfigDict representing this node's location in the topology.
        :param delay_graph: The DelayGraph object representing this cluster's delays.
        """
        self.name = topology.get("id")
        if not self.name:
            self.name = "rs{}".format(ReplTopologyConfig.replsets)
            ReplTopologyConfig.replsets += 1

        self.rs_conf = topology.get("rs_conf", {})
        self.rs_conf_members = []
        self.node_opts = []
        self.configsvr = topology.get("configsvr", False)
        self.delay_graph = delay_graph
        self.auth_settings = mongodb_setup_helpers.mongodb_auth_settings(root_config)

        for opt in topology["mongod"]:
            # save replica set member configs
            self.rs_conf_members.append(copy_obj(opt.get("rs_conf_member", {})))
            # Must add replSetName and clusterRole
            config_file = copy_obj(opt.get("config_file", {}))
            config_file = mongodb_setup_helpers.merge_dicts(
                config_file, {"replication": {"replSetName": self.name}}
            )

            mongod_opt = copy_obj(opt)
            if self.configsvr:
                config_file = mongodb_setup_helpers.merge_dicts(
                    config_file, {"sharding": {"clusterRole": "configsvr"}}
                )
                # The test infrastructure does not set up a separate journal dir for
                # the config server machines.
                mongod_opt["use_journal_mnt"] = False

            mongod_opt["config_file"] = config_file
            self.node_opts.append(
                NodeTopologyConfig(
                    topology=mongod_opt, root_config=root_config, delay_graph=delay_graph
                )
            )

    def get_init_code(self, nodes):
        """
        Return the JavaScript code to configure the replica set.
        :param nodes: a list of Host objects representing nodes in the cluster.
        """
        config = mongodb_setup_helpers.merge_dicts(self.rs_conf, {"_id": self.name, "members": []})
        if self.configsvr:
            config["configsvr"] = True
        for i, node in enumerate(nodes):
            member_conf = mongodb_setup_helpers.merge_dicts(
                self.rs_conf_members[i], {"_id": i, "host": node.hostport_private()}
            )
            config["members"].append(member_conf)
        json_config = json.dumps(config)
        js_string = """
            config = {0};
            assert.commandWorked(rs.initiate(config),
                                 "Failed to initiate replica set!");
            """.format(
            json_config
        )
        return js_string


class ShardedTopologyConfig:
    """
    Class representing the configuration for a single sharded cluster.
    """

    def __init__(self, topology, root_config, delay_graph):
        """
        :param root_config: Root ConfigDict.
        :param topology: ConfigDict representing this node's location in the topology.
        :param delay_graph: The DelayGraph object representing this cluster's delays.
        """
        self.topology = topology
        self.root_config = root_config
        self.delay_graph = delay_graph
        self.disable_balancer = topology.get("disable_balancer", True)
        self.mongos_opts = topology["mongos"]
        self.auth_settings = mongodb_setup_helpers.mongodb_auth_settings(root_config)

        config_type = topology.get("configsvr_type", "csrs")
        if config_type != "csrs":
            raise NotImplementedError("configsvr_type: {}".format(config_type))

        config_opt = {"id": DEFAULT_CSRS_NAME, "configsvr": True, "mongod": topology["configsvr"]}
        self.config_svr_topology = ReplTopologyConfig(
            topology=config_opt, root_config=root_config, delay_graph=delay_graph
        )

        # Since we must support mongo versions prior to 3.6, there may be shards
        # composed of non-replset standalone nodes.
        self.node_shards = []
        self.repl_shards = []
        for topo in topology["shard"]:
            self._create_shard_config(
                topology=topo, delay_graph=delay_graph, root_config=root_config
            )

        self.mongos_topologies = []

    def create_mongos_topologies(self, config_svr_connection_str):
        """
        Creates the topologies for mongos instances in this sharded cluster.
        :param config_svr_connection_str: The connection string for the config
        servers in this cluster.
        """
        for topo in self.topology["mongos"]:
            # add the connection string for the configdb
            config_file = copy_obj(topo.get("config_file", {}))
            configdb_yaml = {"sharding": {"configDB": config_svr_connection_str}}
            config_file = mongodb_setup_helpers.merge_dicts(config_file, configdb_yaml)
            mongos_opt = copy_obj(topo)
            mongos_opt["config_file"] = config_file
            self.mongos_topologies.append(
                NodeTopologyConfig(mongos_opt, self.root_config, self.delay_graph, is_mongos=True)
            )

    def _create_shard_config(self, topology, delay_graph, root_config):
        """
        Create MongoNode, ReplSet, or ShardCluster from topology config
        :param topology: topology config to create - see MongoNode, ReplSet, ShardedCluster docs
        :param root_config: root ConfigDict
        """
        cluster_type = topology["cluster_type"]
        if cluster_type == "standalone":
            self.node_shards.append(
                NodeTopologyConfig(
                    topology=topology, root_config=root_config, delay_graph=delay_graph
                )
            )
        if cluster_type == "replset":
            self.repl_shards.append(
                ReplTopologyConfig(
                    topology=topology, root_config=root_config, delay_graph=delay_graph
                )
            )
