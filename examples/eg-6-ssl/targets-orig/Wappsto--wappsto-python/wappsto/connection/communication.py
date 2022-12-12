"""
The server communication module.

Stores the server communication functionality for Wappsto as well as the
sending and receiving threads.
"""

import os
import socket
import threading
import time
import queue
import ssl
import logging
from . import message_data
from . import receive_data
from . import send_data
from .. import status
from ..errors import wappsto_errors

from .import seluxit_rpc

PACKET_TIMEOUT = 10


class ClientSocket:
    """
    The ClientSocket class that manages connection.

    Stores the sending and receiving threads, certificates as well as connection
    information.
    """

    def __init__(self, data_manager, address, port, path_to_calling_file,
                 wappsto_status, automatic_trace, event_storage):
        """
        Create a client socket.

        Creates a socket instance for the given address and port. Handles
        transfer of data from the instance attributes and methods to the
        specified server. Connection to the server is based on the specified
        address and port.

        Args:
            data_manager: data_manager of DataManager.
            address: Server address.
            port: Server port.
            path_to_calling_file: path to OS directory of calling file.
            wappsto_status: status object.
            handler: instance of handlers.
            automatic_trace: indicates if all messages automaticaly send trace.
            event_storage: instance of event log.

        """
        self.wapp_log = logging.getLogger(__name__)
        self.wapp_log.addHandler(logging.NullHandler())
        self.data_manager = data_manager
        self.path_to_calling_file = path_to_calling_file
        self.ssl_server_cert = os.path.join(path_to_calling_file,
                                            "certificates/ca.crt")
        self.ssl_client_cert = os.path.join(path_to_calling_file,
                                            "certificates/client.crt")
        self.ssl_key = os.path.join(path_to_calling_file,
                                    "certificates/client.key")
        self.address = address
        self.port = port
        self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        self.ssl_context.verify_mode = ssl.CERT_REQUIRED
        self.ssl_context.load_cert_chain(self.ssl_client_cert, self.ssl_key)
        self.ssl_context.load_verify_locations(self.ssl_server_cert)
        self.wappsto_status = wappsto_status

        self.receive_data = receive_data.ReceiveData(self)
        self.receiving_thread = threading.Thread(target=self.receive_data.receive_thread)
        self.receiving_thread.setDaemon(True)

        self.send_data = send_data.SendData(self, automatic_trace)
        self.sending_thread = threading.Thread(target=self.send_data.send_thread)
        self.sending_thread.setDaemon(True)

        self.connected = False
        self.reconnect_inprogres = threading.Lock()
        self.sending_queue = queue.Queue(maxsize=0)
        self.event_storage = event_storage
        self.packet_awaiting_confirm = {}
        self.packet_timeout_list = {}
        self.lock_await = threading.Lock()
        self.set_sockets()

        self.data_manager.network.conn = self

    def set_sockets(self):
        """
        Create socket to communicate with server.

        Creates a socket instance and sets the options for communication.
        Passes the socket to the ssl_wrap method
        """
        self.my_raw_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.my_raw_socket.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_KEEPALIVE,
            1
        )
        if (hasattr(socket, "TCP_KEEPIDLE")
                and hasattr(socket, "TCP_KEEPINTVL")
                and hasattr(socket, "TCP_KEEPCNT")):
            # After 5 idle minutes, start sending keepalives every 1 minutes.
            # Drop connection after 2 failed keepalives
            self.wapp_log.debug("Setting TCP_KEEPIDLE, TCP_KEEPINTVL & TCP_KEEPCNT.")
            self.my_raw_socket.setsockopt(
                socket.SOL_TCP,
                socket.TCP_KEEPIDLE,
                5 * 60
            )
            self.my_raw_socket.setsockopt(
                socket.IPPROTO_TCP,
                socket.TCP_KEEPIDLE,
                5 * 60
            )
            self.my_raw_socket.setsockopt(
                socket.IPPROTO_TCP,
                socket.TCP_KEEPINTVL,
                60
            )
            self.my_raw_socket.setsockopt(
                socket.IPPROTO_TCP,
                socket.TCP_KEEPCNT,
                2
            )

        if hasattr(socket, "TCP_USER_TIMEOUT"):
            self.wapp_log.debug("Setting TCP_USER_TIMEOUT to 30_000ms.")
            self.my_raw_socket.setsockopt(
                socket.IPPROTO_TCP,
                socket.TCP_USER_TIMEOUT,
                30_000
            )
        self.my_socket = self.ssl_wrap()

    def ssl_wrap(self):
        """
        Wrap socket.

        Wraps the socket using the SSL protocol as configured in the SSL
        context, with hostname verification enabled.

        Returns:
        An SSL wrapped socket.

        """
        return self.ssl_context.wrap_socket(
            self.my_raw_socket,
            server_hostname=self.address
        )

    def connect(self):
        """
        Connect to the server.

        Attempts a connection to the server on the provided addres and port.

        Returns:
            A connection flag to denote if the connection was successful or
            not.

        """
        self.connected = False
        try:
            self.wapp_log.info("Trying to Connect.")
            self.my_socket.settimeout(10)
            self.my_socket.connect((self.address, self.port))
            self.connected = True
            self.my_socket.settimeout(None)
            self.wappsto_status.set_status(status.CONNECTED)
            self.wapp_log.info(f"Connected on interface: {self.my_socket.getsockname()[0]}")
            self.send_logged_data()
            return True

        except Exception as e:
            self.wapp_log.error("Failed to connect: {}".format(e))
            return False

    def send_logged_data(self):
        """
        Sends logged data.

        Makes a thread that sends all of the logged data.
        """
        processThread = threading.Thread(target=self.event_storage.send_log, args=(self,))
        processThread.start()

    def initialize_all(self):
        """
        Call initialize_all method in initialize_code module.

        Initializes the object instances on the sending/receiving queue.
        """
        # for device in self.data_manager.network.devices:
        #     for value in device.values:
        #         state = value.get_control_state()
        #         if state is not None:
        #             msg = message_data.MessageData(
        #                 message_data.SEND_CONTROL,
        #                 network_id=state.parent.parent.parent.uuid,
        #                 device_id=state.parent.parent.uuid,
        #                 value_id=state.parent.uuid,
        #                 state_id=state.uuid,
        #                 verb=message_data.GET
        #             )
        #             self.sending_queue.put(msg)

        trace_id = self.send_data.create_trace(self.data_manager.network.uuid)

        message = seluxit_rpc.get_rpc_whole_json(self.data_manager.get_encoded_network(), trace_id)
        self.send_data.create_bulk(message)  # TODO(MBK): This is not conformed.

        msg = "The whole network {} added to Sending queue {}.".format(
            self.data_manager.network.name,
            self.sending_queue
        )
        self.wapp_log.debug(msg)

        self.confirm_initialize_all()

    def _resend(self, _id):
        with self.lock_await:
            data = self.packet_awaiting_confirm[_id]
        self.wapp_log.info("Resending: {}".format(_id))
        self.remove_id_from_confirm_list(_id)
        self.send_data.create_bulk(data)  # NOTE: Are forced to this.

    def add_id_to_confirm_list(self, data):
        """
        Add the message ID to the confirm list.

        Adds the ID of the decoded JSON message to the list of confirmed
        packets. Uses locks to ensure atomicity.

        Args:
            data: JSON communication message data.

        """
        _id = data.get('id')
        timer = threading.Timer(PACKET_TIMEOUT, lambda: self._resend(_id))
        timer.start()
        self.lock_await.acquire()
        self.packet_timeout_list[_id] = timer
        self.packet_awaiting_confirm[_id] = data
        self.lock_await.release()

    def remove_id_from_confirm_list(self, _id):
        """
        Remove the ID from the confirm list.

        Removes the ID of the decoded JSON message from the list of confirmed
        packets. Uses locks to ensure atomicity.

        Args:
            _id: ID to remove from the confirm list.

        """
        self.lock_await.acquire()
        if _id in self.packet_timeout_list:
            self.packet_timeout_list[_id].cancel()
            del self.packet_timeout_list[_id]
        if _id in self.packet_awaiting_confirm:
            del self.packet_awaiting_confirm[_id]
        self.lock_await.release()
        self.poke_send_thread()

    def poke_send_thread(self):
        """Poke the Send thread, to let it know some thing have changed."""
        poke_msg = message_data.MessageData(
            message_data.POKE
        )
        self.sending_queue.put(poke_msg)

    def request_reconnect(self):
        """Reconnect if it is required (Non Blocking)."""
        self.wapp_log.info("Reconnect Requested.")
        if not self.connected and not self.reconnect_inprogres.locked():
            threading.Thread(target=self.reconnect).start()

    def reconnect(self, retry_limit=None, send_reconnect=True):
        """
        Attempt to reconnect.

        Reconnection attempts in the instance of a connection being interrupted.
        """
        with self.reconnect_inprogres:
            if not self.connected:
                self.wappsto_status.set_status(status.RECONNECTING)
                self.connected = False
                attempt = 0
                while not self.connected and (retry_limit is None
                                              or retry_limit > attempt):
                    attempt += 1
                    self.wapp_log.info("Trying to reconnect in 5 seconds")
                    time.sleep(5)
                    self.close()
                    self.set_sockets()
                    self.connect()

                if self.connected is True:
                    self.wapp_log.info("Reconnected with " + str(attempt) + " attempts")
                    if send_reconnect:
                        reconnect = message_data.MessageData(message_data.SEND_RECONNECT)
                        self.sending_queue.put(reconnect)
                else:
                    msg = "Unable to connect to the server[IP: {}, Port: {}]"
                    msg = msg.format(self.address, self.port)
                    raise wappsto_errors.ServerConnectionException(msg)

    def get_object_without_none_values(self, encoded_object):
        """
        Remove objects with None values.

        Gets objects and removes any keys where value is None.

        Args:
            encoded_object: dictionary object.

        """
        # UNSURE(MBK): I feel that there is a more pythonic way of doing this.
        # ERROR(MBK): Is this the source for slowing down the Porcupine, after a month.
        for key, val in list(encoded_object.items()):
            if val is None:
                del encoded_object[key]
            elif isinstance(val, dict):
                self.get_object_without_none_values(val)
                if len(val) == 0:
                    del encoded_object[key]
            elif isinstance(val, list):
                for val_element in val:
                    self.get_object_without_none_values(val_element)
                    if len(val_element) == 0:
                        val.remove(val_element)
                if len(val) == 0:
                    del encoded_object[key]

    def close(self):
        """
        Close the connection.

        Closes the socket object connection.
        """
        self.wapp_log.info("Closing connection...")

        for device in self.data_manager.network.devices:
            for value in device.values:
                if value.timer.is_alive():
                    msg = "Value: {} is no longer periodically sending updates."
                    msg = msg.format(value.uuid)
                    self.wapp_log.debug(msg)
                value.timer.cancel()

        self.connected = False
        if self.my_socket:
            self.my_socket.close()
            self.my_socket = None
        if self.my_raw_socket:
            self.my_raw_socket.close()
            self.my_raw_socket = None

    def confirm_initialize_all(self):
        """
        Confirms that all responses are received.

        Goes through the list saving expected responses and checks if they are
        received.
        """
        while len(self.packet_awaiting_confirm) > 0:
            self.receive_data.receive_message(fail_on_error=True)
