#!/usr/bin/env python
#
# Copyright (c) 2016, Psiphon Inc.
# All rights reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import collections
import string
import random
import time
import sys
import os
import ssl

import psi_utils
import psi_ssh

libcloud_path = os.path.join(os.path.abspath('.'), 'libcloud')
sys.path.insert(0, libcloud_path)

try:
    from libcloud.compute.drivers import vpsnet
    import libcloud.security
except ImportError as error:
    raise error

libcloud.security.CA_CERTS_PATH = ['./libcloud/cacerts/ca-bundle.crt']
if not os.path.exists(libcloud.security.CA_CERTS_PATH[0]):
    print '''
    Could not find valid certificate path.
    See: https://libcloud.readthedocs.org/en/latest/other/ssl-certificate-validation.html
    '''

try:
    libcloud.security.SSL_VERSION = ssl.PROTOCOL_TLSv1_2
except AttributeError:
    raise ImportError("psi_vpsnet requires ssl.PROTOCOL_TLSv1_2")

def get_datacenter_name(datacenter, region):
    datacenter_split = datacenter.split('-')
    datacenter_name = 'VPS.net {}-{}, {}'.format(datacenter_split[-3].strip(), datacenter_split[-2], region)

    return datacenter_name

def get_vpsnet_connection(vpsnet_account):
    '''
        This connects to libclouds VPSNet driver and returns a connection
    '''
    vpsnet_conn = vpsnet.VPSNetNodeDriver(
        key=vpsnet_account.account_id,
        secret=vpsnet_account.api_key,
        secure=True)
    return vpsnet_conn


def refresh_credentials(vpsnet_account, ip_address, generated_root_password,
                        new_root_password, new_stats_password, stats_username):
    ssh = psi_ssh.make_ssh_session(
        ip_address, vpsnet_account.base_ssh_port,
        'root', generated_root_password, None, None,
        )
    ssh.exec_command('echo "root:%s" | chpasswd' % (new_root_password,))
    ssh.exec_command('useradd -M -d /var/log -s /bin/sh -g adm %s' % (stats_username))
    ssh.exec_command('echo "%s:%s" | chpasswd' % (stats_username, new_stats_password))
    ssh.exec_command('rm /etc/ssh/ssh_host_*')
    ssh.exec_command('rm -rf /root/.ssh')
    ssh.exec_command('export DEBIAN_FRONTEND=noninteractive && dpkg-reconfigure openssh-server')
    return ssh.exec_command('cat /etc/ssh/ssh_host_rsa_key.pub')

def set_allowed_users(vpsnet_account, ip_address, password, stats_username):
    ssh = psi_ssh.make_ssh_session(ip_address, vpsnet_account.base_ssh_port, 'root', password, None, None)
    user_exists = ssh.exec_command('grep %s /etc/ssh/sshd_config' % stats_username)
    if not user_exists:
        ssh.exec_command('sed -i "s/^AllowUsers.*/& %s/" /etc/ssh/sshd_config' % stats_username)
        ssh.exec_command('service ssh restart')

def wait_on_action(vpsnet_conn, node, interval=30):
    for attempt in range(10):
        node = vpsnet_conn.get_ssd_node(node.id)
        if 'running' in node.state.lower():
            return True
        else:
            print 'node state : %s.  Trying again in %s' % (node.state, interval)
            time.sleep(int(interval))

    return False


def get_region_name(region):
    '''
        65:  LON-K-SSD:                     London GB (Not available)
        66:  SLC-G-SSD:                     Salt Lake City US (Not available)
        91:  LON-M-SSD:                     London GB (Not available)
        113: SLC-H-SSD:                     Salt Lake City US
        116: (New York) - NYC-A-SSD:        New York US (Not available)
        117: (Los Angeles) - LAX-A-SSD:     Los Angeles US
        118: SLC-K-SSD:                     Salt Lake City US
        119: TOR-A-SSD:                     Toronto CA
        120: AMS-B-SSD:                     Amsterdam NL
        121: LON-P-SSD:                     London GB (Not available)
        124: (Miami) - MIA-A-SSD:           Miami US
        125: (Chicago) - CHI-C-SSD:         Chicago US
        126: (Dallas) - DAL-B-SSD           Dallas US
        127: LON-R-SSD                      London GB
        128: VAN-A-SSD                      Vancouver CA
        129: (New York) - NYC-B-SSH         New York US
        130: PHX-A-SSD                      City of Phoenix US
        131: (Seattle) - SEA-B-SSD          Seattle US
        132: ATL-G-SSD                      Atlanta US
        133: (New York) - NYC-C-SSD         New York US
        134: LON-Q-SS                       London GB
        135: FRA-B-SSD                      Frankfurt DE
    '''
    if region['cloud_id'] in [65, 91, 121, 127, 134]:
        return 'GB'
    if region['cloud_id'] in [66, 113, 116, 117, 118, 124, 125, 126, 129, 130, 131, 132, 133]:
        return 'US'
    if region['cloud_id'] in [119, 128]:
        return 'CA'
    if region['cloud_id'] in [120]:
        return 'NL'
    if region['cloud_id'] in [135]:
        return 'DE'
    return ''


def get_server(account, node_id):
    '''
        get_server returns a vps.net node object
    '''
    node = None
    try:
        vpsnet_conn = get_vpsnet_connection(account)
        node = vpsnet_conn.get_ssd_node(node_id)
    except Exception as e:
        raise e

    return node


def get_servers(account):
    nodes = list()
    try:
        vpsnet_conn = get_vpsnet_connection(account)
        nodes = vpsnet_conn.list_ssd_nodes_basic()
    except Exception as e:
        raise e
    return [(str(node.id), node.name) for node in nodes]


def remove_server(vpsnet_account, node_id):
    '''
        remove_server destroys a node using vps.net API calls
    '''
    try:
        vpsnet_conn = get_vpsnet_connection(vpsnet_account)
        node = vpsnet_conn.get_ssd_node(node_id)
        result = vpsnet_conn.delete_ssd_node(node)
        if not result:
            raise Exception('Could not destroy node: %s' % str(node_id))
    except KeyError as e:
        if e.message == 'virtual_machine':
            # The server has already been deleted
            pass
        else:
            raise e
    except Exception as e:
        raise e


def launch_new_server(vpsnet_account, is_TCS, _, multi_ip=False, datacenter_city=None):
    """
        launch_new_server is called from psi_ops.py to create a new server.
    """

    # TODO-TCS: select base image based on is_TCS flag
    base_image_id = '9704' # For VPS
    # base_image_id = '8850' # For Cloud Server

    try:
        VPSNetHost = collections.namedtuple('VPSNetHost',
                                            ['ssd_vps_plan', 'fqdn',
                                             'system_template_id',
                                             'cloud_id', 'backups_enabled',
                                             'rsync_backups_enabled',
                                             'licenses'])

        vpsnet_conn = get_vpsnet_connection(vpsnet_account)

        # Get a list of regions (clouds) that can be used
        vpsnet_clouds = vpsnet_conn.get_available_ssd_clouds()
        # vpsnet_clouds = vpsnet_conn.get_available_clouds()

        # Check each available cloud for a psiphon template to use.
        # Populate a list of templates and the cloud IDs.
        psiphon_templates = list()
        print 'Available Regions:\n'
        for region in vpsnet_clouds:
            print '%s -> %s' % (region['cloud']['id'], region['cloud']['label'])
            for template in region['cloud']['system_templates']:
                if 'tcs' in template['label'].lower() and str(template['id']) == base_image_id:
                    print '\tFound psiphon template id %s in region %s' % (
                        template['id'], region['cloud']['id'])
                    template['cloud_id'] = region['cloud']['id']
                    template['cloud_label'] = region['cloud']['label']
                    psiphon_templates.append(template)

        if datacenter_city != None:
            region_template = [s for s in psiphon_templates if datacenter_city in s['cloud_label'].lower()][0]
        else:
            region_template = random.choice(psiphon_templates) 
        VPSNetHost.cloud_id = region_template['cloud_id']
        VPSNetHost.system_template_id = region_template['id']

        print 'Using template: %s with cloud_id: %s' % (
            VPSNetHost.system_template_id, VPSNetHost.cloud_id)

        '''
            package/plan for the new SSD server.
            (VPS 1GB - 1, VPS 2GB - 2, VPS 4GB - 3, VPS 8GB - 4, VPS 16GB - 5)
        '''

        host_id = 'vn-' + get_region_name(region_template).lower() + ''.join(random.choice(string.ascii_lowercase) for x in range(8))

        VPSNetHost.name = str(host_id)
        VPSNetHost.ssd_vps_plan = vpsnet_account.base_ssd_plan
        VPSNetHost.fqdn = str(host_id + '.vps.net')
        VPSNetHost.backups_enabled = False
        VPSNetHost.rsync_backups_enabled = False
        VPSNetHost.licenses = None

        node = vpsnet_conn.create_ssd_node(
            fqdn=VPSNetHost.fqdn,
            image_id=VPSNetHost.system_template_id,
            cloud_id=VPSNetHost.cloud_id,
            size=VPSNetHost.ssd_vps_plan,
            backups_enabled=VPSNetHost.backups_enabled,
            rsync_backups_enabled=VPSNetHost.rsync_backups_enabled,
            )

        # node = vpsnet_conn.create_node(
        #     name=VPSNetHost.name,
        #     image_id=VPSNetHost.system_template_id,
        #     cloud_id=VPSNetHost.cloud_id,
        #     size=VPSNetHost.ssd_vps_plan,
        #     backups_enabled=VPSNetHost.backups_enabled,
        #     rsync_backups_enabled=VPSNetHost.rsync_backups_enabled,
        #     ex_fqdn=VPSNetHost.fqdn,
        #     )
        
        if not wait_on_action(vpsnet_conn, node, 30):
            raise "Could not power on node"
        else:
            node = vpsnet_conn.get_ssd_node(node.id)
            #node = vpsnet_conn.get_node(node.id)

        generated_root_password = node.extra['password']

        # Get the Node IP address
        if isinstance(node.public_ips, list):
            for public_ip in node.public_ips:
                if 'ip_address' in (public_ip and public_ip['ip_address']):
                    public_ip_address = public_ip['ip_address']['ip_address']

        if is_TCS:
            stats_username = psi_utils.generate_stats_username()
        elif not is_TCS:
            stats_username = vpsnet_account.base_stats_username

        new_root_password = psi_utils.generate_password()
        new_stats_password = psi_utils.generate_password()
        node_public_key = refresh_credentials(vpsnet_account, public_ip_address,
                                              generated_root_password,
                                              new_root_password, new_stats_password, stats_username)
        set_allowed_users(vpsnet_account, public_ip_address, new_root_password, stats_username)
    except Exception as e:
        print type(e), str(e)
        if node is not None:
            remove_server(vpsnet_account, node.id)
        else:
            print type(e), "No node to be destoryed: %s", str(node)
        raise

    return (
        host_id,
        is_TCS,
        'NATIVE' if is_TCS else None,
        None,
        node.id,
        public_ip_address,
        vpsnet_account.base_ssh_port,
        'root',
        new_root_password,
        ' '.join(node_public_key.split(' ')[:2]),
        stats_username,
        new_stats_password,
        get_datacenter_name(region_template['cloud_label'], get_region_name(region_template)),
        get_region_name(region_template),
        None, None
        )
