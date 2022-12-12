# Copyright (c) 2020 Cable Television Laboratories, Inc.
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
import os
from abc import ABC, abstractmethod
from threading import Thread

import grpc
import tofino.bfrt_grpc.client as bfrt_client
import yaml
from bfrt_grpc.client import KeyTuple, DataTuple
from google.rpc import code_pb2, status_pb2
from tofino.bfrt_grpc import bfruntime_pb2

from trans_sec.switch import SwitchConnection

MSG_LOG_MAX_LEN = 1024

logger = logging.getLogger('switch')


class BFRuntimeSwitch(SwitchConnection, ABC):
    def __init__(self, sw_info, client_id=0, is_master=True):
        super(BFRuntimeSwitch, self).__init__(sw_info)

        logger.info('Connecting to the BFRT server @ [%s], client_id [%s],'
                    ' device_id [%s]',
                    self.grpc_addr, client_id, self.device_id)
        self.interface = bfrt_client.ClientInterface(
            grpc_addr=self.grpc_addr, client_id=client_id,
            device_id=self.device_id, is_master=is_master)
        self.target = bfrt_client.Target(
            device_id=self.device_id, pipe_id=0xffff)

        if self.sw_info.get('arch') and self.sw_info['arch'] != 'v1model':
            self.prog_name = "{}_{}".format(self.name, self.sw_info['arch'])
        else:
            self.prog_name = "{}}".format(self.name, self.sw_info['arch'])

        self.bfrt_info = self.interface.bfrt_info_get(self.prog_name)

        p4_name = self.bfrt_info.p4_name_get()
        logger.info('Binding pipeline config with - [%s]', p4_name)
        self.interface.bind_pipeline_config(self.bfrt_info.p4_name_get())

        self.digest_thread = Thread(target=self.receive_digests)

    def start(self, ansible_inventory, controller_user):
        logger.info('Starting switch - [%s]', self.name)
        self.interface.clear_all_tables()
        self.__configure_ports(ansible_inventory, controller_user)
        self.add_switch_id()
        self.digest_thread.start()
        self.update_arp_multicast(ports=self.__find_node_ports())
        self.__setup_default_port()

    def stop(self):
        self.digest_thread.join()

    def __configure_ports(self, ansible_inventory, controller_user):
        logger.info('Configuring switch ports using inventory - [%s]',
                    ansible_inventory)
        with open(ansible_inventory, 'r') as inv_file:
            inv_dict = yaml.safe_load(inv_file)

        trans_sec_dir = inv_dict['all']['vars']['orch_trans_sec_dir']
        playbook = "{}/playbooks/tofino/conf_switch_ports.yml".format(
            trans_sec_dir)
        extra_vars = {
            "host_val": self.name,
            "ports": self.sw_info['tunnels']
        }
        cmd = 'su - {} -c "/usr/local/bin/ansible-playbook -i {} {} '\
              '--extra-vars=\\"{}\\""'.format(
                controller_user, ansible_inventory, playbook, str(extra_vars))
        ret_val = os.system(cmd)
        if ret_val != 0:
            logger.error('os.system command [%s] failed with - [%s]',
                         cmd, ret_val)
        logger.info('Playbook command [%s] return value - [%s]', cmd, ret_val)

    def update_arp_multicast(self, node_id=1, rid=1, lags=[], mgid=1,
                             mc_nids=[1], l1_xids=[0], ports=None):
        if not ports:
            ports = self.__find_node_ports()
        self.__update_pre_tbl(node_id, ports, rid, lags)
        self.__update_mgid_tbl(mgid, mc_nids, l1_xids)

    def __update_pre_tbl(self, node_id, ports, rid=1, lags=[]):
        logger.info('Deleting and adding multicast entries to $pre.node')
        pre_table = self.get_table('$pre.node')
        pre_key = [pre_table.make_key(
                    [KeyTuple('$MULTICAST_NODE_ID', node_id)])]
        try:
            pre_table.entry_del(self.target, pre_key)
        except Exception as e:
            logger.debug('Ignore me - [%s]', e)
            pass

        try:
            pre_table.entry_add(
                self.target, pre_key,
                [pre_table.make_data([
                    DataTuple('$MULTICAST_RID', rid),
                    DataTuple('$DEV_PORT', int_arr_val=ports),
                    DataTuple('$MULTICAST_LAG_ID', int_arr_val=lags),
                ])]
            )
        except Exception as e:
            if 'ALREADY_EXISTS' in str(e):
                pass
            else:
                logger.error('Unexpected error inserting into table %s - [%s]',
                             '$pre.node', e)
                raise e

    def __update_mgid_tbl(self, mgid, mc_nids, l1_xids):
        mg_id_table = self.get_table('$pre.mgid')
        mg_id_key = [mg_id_table.make_key([KeyTuple('$MGID', mgid)])]
        try:
            mg_id_table.entry_del(self.target, mg_id_key)
        except Exception as e:
            logger.debug('Ignore me - [%s]', e)
            pass

        try:
            mg_id_table.entry_add(
                self.target, mg_id_key,
                [mg_id_table.make_data([
                    DataTuple('$MULTICAST_NODE_ID', int_arr_val=mc_nids),
                    DataTuple('$MULTICAST_NODE_L1_XID_VALID',
                              bool_arr_val=[False]),
                    DataTuple('$MULTICAST_NODE_L1_XID', int_arr_val=l1_xids),
                ])]
            )
        except Exception as e:
            if 'ALREADY_EXISTS' in str(e):
                pass
            else:
                logger.error('Unexpected error inserting into table %s - [%s]',
                             '$pre.mgid', e)
                raise e
        logger.info('Done with MC entries')

    def get_arp_multicast_ports(self, node_id=1):
        logger.info('Retrieving multicast entries from switch')
        mg_id_table = self.get_table('$pre.node')
        match_keys = [mg_id_table.make_key([KeyTuple('$MULTICAST_NODE_ID',
                                                     node_id)])]
        entries = mg_id_table.entry_get(self.target, match_keys)

        out_ports = list()
        for data, key in entries:
            if '$DEV_PORT' in data:
                out_ports.append(data.to_dict()['$DEV_PORT'])

        logger.info('Multicast ports returned - [%s]', out_ports)
        return out_ports

    def __setup_default_port(self):
        dflt_port = self.__find_dflt_port()
        if dflt_port:
            self.update_default_port(dflt_port)

    def __find_node_ports(self):
        """
        Returns a list of all active ports as configured in the "tunnels" list
        section of self.sw_info dict that are not == 1
        :return:
        """
        return self.__find_tunnel_ports()

    def __find_dflt_port(self):
        """
        Returns the default port number or None if not defined
        :return:
        """
        return self.__find_tunnel_ports('default')[0]

    def __find_tunnel_ports(self, port_type=None):
        """
        Returns a list of all active ports as configured in the "tunnels" list
        section of self.sw_info dict that are not == 1
        :return:
        """
        out = list()
        for tunnel in self.sw_info['tunnels']:
            tunnel_port = int(tunnel['switch_port'])
            if tunnel_port != 1 and tunnel.get('type', None) == port_type:
                out.append(tunnel_port)
        return out

    @abstractmethod
    def receive_digests(self):
        raise NotImplemented

    @abstractmethod
    def update_default_port(self, dflt_port):
        raise NotImplemented

    def get_table(self, name):
        return self.bfrt_info.table_get(name)

    def get_table_id(self, name):
        table = self.get_table(name)
        if table:
            logger.debug('table id - [%s]', table.info.id)
            return table.info.id

    def insert_table_entry(self, table_name, action_name, key_fields=None,
                           data_fields=None):
        """
        Insert a new table entry
        @param table_name : Table name.
        @param action_name : Action name.
        @param key_fields : List of bfrt_grpc.client.KeyTuple objects.
        @param data_fields : List of bfrt_grpc.client.DataTuple objects.
        """

        table = self.get_table(table_name)
        if table:
            key = table.make_key(key_fields)
            data = table.make_data(data_fields, action_name)
            logger.info('Inserting keys - [%s], data - [%s] into table [%s]',
                        key_fields, data_fields, table_name)
            table.entry_add(self.target, [key], [data])

    def delete_table_entry(self, table_name, key_fields=None):
        """
        Delete an existing table entry
        @param table_name : Table name.
        @param key_fields : List of bfrt_grpc.client.KeyTuple objects.
        """
        table = self.get_table(table_name)
        if table:
            key = table.make_key(key_fields)
            table.entry_del(self.target, [key])


def parseGrpcErrorBinaryDetails(grpc_error):
    if grpc_error.code() != grpc.StatusCode.UNKNOWN:
        return None

    error = None
    # The gRPC Python package does not have a convenient way to access the
    # binary details for the error: they are treated as trailing metadata.
    for meta in grpc_error.trailing_metadata():
        if meta[0] == "grpc-status-details-bin":
            error = status_pb2.Status()
            error.ParseFromString(meta[1])
            break
    if error is None:  # no binary details field
        return None
    if len(error.details) == 0:
        # binary details field has empty Any details repeated field
        return None

    indexed_p4_errors = []
    for idx, one_error_any in enumerate(error.details):
        p4_error = bfruntime_pb2.Error()
        if not one_error_any.Unpack(p4_error):
            return None
        if p4_error.canonical_code == code_pb2.OK:
            continue
        indexed_p4_errors += [(idx, p4_error)]
    return indexed_p4_errors


def printGrpcError(grpc_error):
    status_code = grpc_error.code()
    logger.error("gRPC Error %s %s",
                 grpc_error.details(),
                 status_code.name)

    if status_code != grpc.StatusCode.UNKNOWN:
        return
    bfrt_errors = parseGrpcErrorBinaryDetails(grpc_error)
    if bfrt_errors is None:
        return
    logger.error("Errors in batch:")
    for idx, bfrt_error in bfrt_errors:
        code_name = code_pb2._CODE.values_by_number[
            bfrt_error.canonical_code].name
        logger.error("\t* At index %d %s %s\n",
                     idx, code_name, bfrt_error.message)
    return bfrt_errors
