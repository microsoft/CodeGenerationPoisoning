#!/usr/bin/env python3

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
import argparse
import getmac
from python_arptable import ARPTABLE
import logging
import random
import time
from logging import getLogger, basicConfig
from time import sleep

import ipaddress
import yaml
from scapy.all import get_if_list, get_if_hwaddr
from scapy.layers.inet import IP, UDP, TCP
from scapy.layers.inet6 import IPv6
from scapy.layers.l2 import Ether
from scapy.sendrecv import sendp

# Logger stuff
import trans_sec.consts
from trans_sec.packet.inspect_layer import (
    IntShim, IntHeader, IntMeta1, IntMeta2, SourceIntMeta, UdpInt)

logger = getLogger('send_packets')

FORMAT = '%(levelname)s %(asctime)-15s %(filename)s %(message)s'


def get_first_if():
    for iface in get_if_list():
        if iface != 'lo':
            return iface
    raise Exception('No NIC to send packets to')


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-d', '--continuous',
        help='When true, count disregarded and packets will send indefinitely',
        type=bool, required=False, default=False)
    parser.add_argument(
        '-c', '--count', help='Number of packets to send for each burst',
        type=int, default=1, required=False)
    parser.add_argument(
        '-i', '--interval',
        help='How often to send packets in seconds (Default = 1)',
        type=float, required=False, default=1)
    parser.add_argument(
        '-y', '--delay', help='Delay before starting run (Default = 0',
        type=int, required=False, default=0)
    parser.add_argument(
        '-r', '--destination', help='Destination IP address', required=True)
    parser.add_argument(
        '-e', '--src-mac', help='Source MAC Address', required=False,
        default=None)
    parser.add_argument(
        '-sa', '--source-addr', help='Source IP Address', required=False,
        default=None)
    parser.add_argument(
        '-sp', '--source-port', type=int, default=random.randint(49152, 65535),
        help='Source port else it will be random')
    parser.add_argument(
        '-p', '--port', help='Destination port', type=int, required=True)
    parser.add_argument('-m', '--msg', help='Message to send', required=True)
    parser.add_argument(
        '-l', '--loglevel', required=False, default='INFO',
        help='Log Level <DEBUG|INFO|WARNING|ERROR> defaults to INFO')
    parser.add_argument(
        '-f', '--logfile', help='File to log to defaults to console',
        required=False, default=None)
    parser.add_argument(
        '-z', '--interface', required=False, default=None,
        help='Linux named ethernet device. Defaults to first one found')
    parser.add_argument(
        '-s', '--switch_ethernet',
        help='Destination MAC. Defaults to ff:ff:ff:ff:ff:ff',
        required=False, default='ff:ff:ff:ff:ff:ff')
    parser.add_argument(
        '-ih', '--int-hdr-file', required=False,
        help='Switch Ethernet Interface. Defaults to ff:ff:ff:ff:ff:ff')
    parser.add_argument(
        '-it', '--iterations',
        help='Number of iterations of packet groups to send',
        required=False, default=1, type=int)
    parser.add_argument(
        '-itd', '--iter-delay',
        help='Seconds between iterations of packet groups to be sent',
        required=False, default=1, type=int)
    parser.add_argument(
        '-pr', '--protocol', dest='protocol', required=False, type=str,
        default='UDP', choices=['TCP', 'UDP'],
        help='The packet protocol to generate. [TCP|UDP - default]')
    args = parser.parse_args()
    return args


def device_send(args):
    logger.info('Begin sending packets')

    interface = args.interface
    if not interface:
        interface = get_first_if()
    logger.info('Sending packets to intf - [%s]', args.interface)

    logger.info('Delaying %d seconds' % args.delay)
    sleep(args.delay)

    pkt = __create_packet(args, interface)
    if args.continuous:
        logger.info('Sending a packet to %s every %s',
                    interface, args.interval)
        sendp(pkt, iface=interface, verbose=2, inter=args.interval, loop=1)
    else:
        logger.info('Starting iter loop for iterations %s', args.iterations)
        for i in range(0, args.iterations):
            logger.info('Iteration %s', i)
            logger.info('Sending %s packets to %s every %s',
                        args.count, interface, args.interval)
            sendp(pkt, iface=interface, verbose=2, count=args.count,
                  inter=args.interval)
            if i != args.iterations - 1:
                time.sleep(args.iter_delay)

    logger.info('Done')
    return


def __create_packet(args, interface):
    logger.info('Send to destination - [%s] on interface - [%s]',
                args.destination, interface)

    src_mac = args.src_mac
    if not src_mac:
        src_mac = get_if_hwaddr(interface)
    logger.info('Device mac - [%s]', src_mac)

    ip_ver = 4
    ip_addr = ipaddress.ip_address(args.destination)
    logger.info('Destination IP addr [%s] ([%s]) type - [%s]',
                args.destination, args.destination, ip_addr.__class__)
    if isinstance(ip_addr, ipaddress.IPv6Address):
        ip_ver = 6
    logger.info('IP version is - [%s]', ip_ver)

    if args.int_hdr_file:
        pkt = __gen_int_pkt(args=args, ip_ver=ip_ver, src_mac=src_mac)
    else:
        pkt = __gen_std_pkt(args=args, ip_ver=ip_ver, src_mac=src_mac)

    if args.protocol == 'TCP':
        logger.info('Generating a TCP packet')
        pkt = pkt / TCP(dport=args.port, sport=args.source_port)
    elif args.protocol == 'UDP':
        logger.info('Generating a UDP packet')
        pkt = pkt / UDP(dport=args.port, sport=args.source_port)

    logger.info('Packet to emit - [%s]', pkt.summary())

    return pkt / args.msg


def __gen_std_pkt(args, ip_ver, src_mac):
    ip_hdr = None
    if ip_ver == 4:
        if args.protocol == 'TCP':
            ip_hdr = IP(dst=args.destination, src=args.source_addr,
                        proto=trans_sec.consts.TCP_PROTO)
        elif args.protocol == 'UDP':
            ip_hdr = IP(dst=args.destination, src=args.source_addr,
                        proto=trans_sec.consts.UDP_PROTO)
    else:
        if args.protocol == 'TCP':
            ip_hdr = IPv6(dst=args.destination, src=args.source_addr,
                          nh=trans_sec.consts.TCP_PROTO)
        elif args.protocol == 'UDP':
            ip_hdr = IPv6(dst=args.destination, src=args.source_addr,
                          nh=trans_sec.consts.UDP_PROTO)

    dst_mac = __get_dst_mac(args)

    logger.info('Making packet with dst_mac - [%s]', dst_mac)
    if ip_ver == 4:
        pkt = Ether(src=src_mac, dst=dst_mac,
                    type=trans_sec.consts.IPV4_TYPE)
    else:
        pkt = Ether(src=src_mac, dst=dst_mac,
                    type=trans_sec.consts.IPV6_TYPE)

    if ip_hdr:
        pkt = pkt / ip_hdr

    return pkt


def __get_dst_mac(args):
    # Determine the destination MAC
    dst_mac = __get_dst_mac_from_ip(args.destination)
    logger.info('MAC from ARP table - [%s]', dst_mac)
    if not dst_mac or dst_mac == 'ff:ff:ff:ff:ff:ff':
        dst_mac = args.switch_ethernet

    logger.info('DST MAC - [%s]', dst_mac)
    return dst_mac


def __get_dst_mac_from_ip(ip_addr_str):
    ip_addr = ipaddress.ip_address(ip_addr_str)
    logger.info('ip_addr class - [%s]', ip_addr.__class__)
    out_mac = None
    if ip_addr.version == 4:
        logger.info('MAC from ipv4 ARPTABLE')
        for arp_entry in ARPTABLE:
            if arp_entry['IP address'] == ip_addr_str:
                out_mac = arp_entry['HW address']
    else:
        logger.info('mac from ipv6 - [%s]', ip_addr_str)
        out_mac = getmac.get_mac_address(ip=str(ip_addr), network_request=True)

    logger.info('out_mac - [%s]', out_mac)
    return out_mac


def __gen_int_pkt(args, ip_ver, src_mac):
    int_data = __read_yaml_file(args.int_hdr_file)
    int_hops = len(int_data['meta'])
    shim_len = 4 + 3 + int_hops - 1
    logger.info('Int data to add to packet - [%s]', int_data)
    udp_int_len = None
    # TODO - Find a better way to calculate PAYLOAD_LEN using args.msg
    if args.protocol == 'UDP':
        udp_int_len = trans_sec.consts.UDP_INT_HDR_LEN + (shim_len * 4) \
                      + trans_sec.consts.UDP_HDR_LEN \
                      + trans_sec.consts.PAYLOAD_LEN
    elif args.protocol == 'TCP':
        udp_int_len = trans_sec.consts.UDP_INT_HDR_LEN + (shim_len * 4) \
                      + trans_sec.consts.TCP_HDR_LEN \
                      + trans_sec.consts.PAYLOAD_LEN
    ipv4_len = trans_sec.consts.IPV4_HDR_LEN + udp_int_len
    ipv6_len = trans_sec.consts.IPV6_HDR_LEN + udp_int_len
    dst_mac = __get_dst_mac(args)
    if ip_ver == 4:
        pkt = (Ether(src=src_mac, dst=dst_mac,
                     type=trans_sec.consts.IPV4_TYPE) /
               IP(dst=args.destination, src=args.source_addr, len=ipv4_len,
                  proto=trans_sec.consts.UDP_PROTO))
    else:
        pkt = (Ether(src=src_mac, dst=dst_mac,
                     type=trans_sec.consts.IPV6_TYPE) /
               IPv6(dst=args.destination, src=args.source_addr,
                    nh=trans_sec.consts.UDP_PROTO, plen=ipv6_len))

    # Add UDP INT header
    pkt = pkt / UdpInt(len=udp_int_len)

    # Create INT Shim header
    if args.protocol == 'UDP':
        pkt = pkt / IntShim(length=shim_len,
                            next_proto=trans_sec.consts.UDP_PROTO)
    elif args.protocol == 'TCP':
        pkt = pkt / IntShim(length=shim_len,
                            next_proto=trans_sec.consts.TCP_PROTO)

    if int_hops > 0:
        pkt = pkt / IntHeader()
        ctr = 0
        for int_meta in int_data['meta']:
            logger.info('Adding int_meta - [%s] to INT data', int_meta)

            if ctr == 0 and not int_meta.get('orig_mac'):
                logger.info('Adding IntMeta1')
                pkt = pkt / IntMeta1(switch_id=int_meta['switch_id'])
            elif ctr > 0 and not int_meta.get('orig_mac'):
                logger.info('Adding IntMeta2')
                pkt = pkt / IntMeta2(switch_id=int_meta['switch_id'])
            elif int_meta.get('orig_mac'):
                orig_mac = int_meta.get('orig_mac')
                logger.info('Adding Source INT Meta with orig_mac - [%s]',
                            orig_mac)
                pkt = pkt / SourceIntMeta(
                    switch_id=int_meta['switch_id'],
                    orig_mac=orig_mac)
            ctr += 1

    return pkt


def __read_yaml_file(config_file_path):
    """
    Reads a yaml file and returns a dict representation of it
    :return: a dict of the yaml file
    """
    logger.debug('Attempting to load configuration file - ' + config_file_path)
    config_file = None
    try:
        with open(config_file_path, 'r') as config_file:
            config = yaml.safe_load(config_file)
            logger.info('Loaded configuration')
        return config
    finally:
        if config_file:
            logger.info('Closing configuration file')
            config_file.close()


if __name__ == '__main__':
    cmd_args = get_args()
    numeric_level = getattr(logging, cmd_args.loglevel.upper(), None)
    if cmd_args.logfile:
        basicConfig(format=FORMAT, level=numeric_level,
                    filename=cmd_args.logfile)
    else:
        basicConfig(format=FORMAT, level=numeric_level)

    logger.info('Starting Send with args - [%s]', cmd_args)
    device_send(cmd_args)
