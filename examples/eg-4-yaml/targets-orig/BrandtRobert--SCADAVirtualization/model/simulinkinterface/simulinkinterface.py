import selectors
import yaml
import socket
from model.datachannels import PublishQueue
from model.plc import LogicController
from model.simulinkinterface import simtimeoracle
import multiprocessing
import os
import struct
import binascii
from model.logger import Logger


class SimulinkInterface:
    def __init__(self, config_path, send_port=5000):
        self.controller_ps = []
        self.config = self.read_config(config_path)
        self.selector = selectors.DefaultSelector()
        self.publish_queue = PublishQueue()
        self.udp_send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_send_socket.bind(('', send_port))
        self.logger = Logger('InterfaceLogger', '../logger/logs/interface_log.txt')
        # Used for sim time oracle which is currently disabled
        # self.time_oracle = None

    def read_config(self, config_path):
        """
            Read and parse the .yaml configuration file.
        :param config_path: the path to the specific yaml file
        :return:
        """
        with open(config_path, 'r') as stream:
            try:
                config_yaml = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
                exit(1)
        # if not config_yaml['settings']:
        #     print("Failed to read config... no settings in file")
        #     exit(1)
        # if not config_yaml['settings']['send_port']:
        #     print("Failed to read config... no send_port in settings")
        #     exit(1)
        return config_yaml

    def create_plcs(self):
        """
            Creates PLC(s) based on the .yaml configuration file.
            Each PLC spawns several "worker" processes which listen for incoming simulink data
                through a predefined publish / subscribe mechanism.
            The register_workers function creates the server sockets for each worker, and registers them to
            the main selector. These workers also subscribe to receive the data coming to their "listening port"
            by registering themselves with the publish queue.
        :return:
        """
        for plc_name, plc_config in self.config.items():
            if plc_name == 'time_oracle':
                continue
            controller = LogicController(plc_name, plc_config)
            controller.register_workers(self.selector, self.publish_queue)
            controller_ps = multiprocessing.Process(target=controller.start_plc, daemon=True, name=plc_name)
            self.controller_ps.append(controller_ps)

    # def init_time_oracle(self):
    #     """
    #     Read simtime oracle source for more information, tries to resolve the difference between real
    #         and simulated time using a pseudo-NTP approach. You can work on this if you'd like to centralize the timer
    #         to the interface instead of using a virtual PLC (oracle PLC) to manage simulation timestamps.
    #     :return:
    #     """
    #     timer_conf = self.config['time_oracle']
    #     time_oracle = simtimeoracle.SimulationTimeOracle(timer_conf['receive_port'], timer_conf['respond_port'])
    #     return time_oracle, multiprocessing.Process(target=time_oracle.start, name='Time Oracle', daemon=True)

    # def _accept_connection(self, sock: socket.socket):
    #     """
    #         !!!! NO LONGER USED IN UDP Implementation !!!!
    #         Upon receiving a new connection from simulink register this connection to our selector and
    #         it's respective data.
    #     :param sock:
    #     :return:
    #     """
    #     conn, addr = sock.accept()
    #     print("New connection from {}".format(addr))
    #     conn.setblocking(False)
    #     self.selector.register(conn, selectors.EVENT_READ, {"connection_type": "client_connection",
    #                                                         "channel": addr[1]})

    def _read_and_publish(self, connection: socket, channel: str):
        """
            Reads data from simulink.
            |----------------------|
            |--- 64 bit timestamp -|
            |--- 64 bit reading ---|
            |----------------------|
        :param connection: the connection from a simulink block
        :param channel: the channel to publish this data to on the publish queue
        """
        data = connection.recv(16)  # Should be ready
        if data:
            sim_time, reading = struct.unpack(">dd", data)
            sim_time = int(sim_time)
            self.publish_queue.publish((sim_time, reading), channel)
        else:
            print('closing', connection)
            self.selector.unregister(connection)
            connection.close()

    def _send_response(self, read_pipe, host: str, port: int):
        """
            Reads from the worker pipe and forwards the data to the respective simulink block
            based on the host and port specified.
        :param read_pipe: a pipe connecting the worker thread to the main simulink selector
        :param host: ip / hostname to send data
        :param port: port number that the host is listening on
        :return:
        """
        response_data = os.read(read_pipe, 128)
        self.logger.info("Sending response {} to {}:{}".format(binascii.hexlify(response_data), host, port))
        self.udp_send_socket.sendto(response_data, (host, port))

    def service_connection(self, key):
        """
            Based on the information in the key['connection_type'] route take the correct action.
            For server_sockets read the data and publish to the queue.
            For responses read the appropriate data from the response pipe and forward to simulink.
        :param key: The key associated with the file object registered in the selector
        :return:
        """
        connection = key.fileobj
        connection_type = key.data['connection_type']
        if connection_type == 'server_socket':
            channel = key.data['channel']
            self._read_and_publish(connection, channel)
        if connection_type == 'response':
            read_pipe = key.fileobj
            # The address to respond to should be registered along with the pipe object
            host, port = key.data['respond_to']
            self._send_response(read_pipe, host, port)

    def start_server(self):
        """
            Set up the virtual PLC(s) and their respective worker processes / threads.
            Initialize the time oracle.
            Once setup, start the PLC(s) to begin listening for data.
            Then start the selector loop, waiting for new data and servicing incoming responses.
        :return:
        """
        # Time oracle stuff is now manage in PLC sensors
        # self.time_oracle, time_oracle_ps = self.init_time_oracle()
        # time_oracle_ps.start()

        self.create_plcs()
        for plc in self.controller_ps:
            self.logger.info('Starting controller: {}'.format(plc))
            plc.start()

        while True:
            events = self.selector.select()
            for key, mask in events:
                self.service_connection(key)
