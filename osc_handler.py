"""
This module provides a class to handle OSC (Open Sound Control) messages using a Unix socket.

The `OSCServerHandler` class initializes an OSC server that listens for messages on a specified
Unix socket.
It buffers incoming OSC messages in a queue and provides methods to start and stop the server.
"""

import logging
import os
import queue
from oscpy.server import OSCThreadServer


class OSCServerHandler:
    """
    A class to handle OSC (Open Sound Control) messages using a Unix socket.

    Attributes:
        unix_socket_path (str): The path to the Unix socket.
        osc_buffer (queue.Queue): A queue to buffer incoming OSC messages.
        osc_server (OSCThreadServer): The OSC server instance.
    """

    def __init__(self, unix_socket_path):
        """
        Initializes the OSCServerHandler with the given Unix socket path.

        Args:
            unix_socket_path (str): The path to the Unix socket.
        """
        self.unix_socket_path = unix_socket_path
        self.osc_buffer = queue.Queue()
        self.osc_server = OSCThreadServer(
            default_handler=self._default_handler)

    def _default_handler(self, address, *values):
        """
        The default handler for OSC messages. Puts the message into the buffer.

        Args:
            address (str): The OSC address.
            *values: The OSC message values.
        """
        self.osc_buffer.put((address, values))

    def start(self):
        """
        Starts the OSC server and begins listening for messages on the Unix socket.
        """
        if os.path.exists(self.unix_socket_path):
            os.remove(self.unix_socket_path)
        self.osc_server.listen(
            address=self.unix_socket_path, default=True, family='unix')
        logging.info("Listening for OSC messages on %s", self.unix_socket_path)

    def stop(self):
        """
        Stops the OSC server.
        """
        self.osc_server.stop()
        logging.info("OSC server stopped.")
