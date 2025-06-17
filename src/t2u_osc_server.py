import socket
import threading
import logging
from oscpy.client import OSCClient


class Tcp2UnixOscServer:
    """
    A TCP to Unix socket server that forwards data from TCP clients to a Unix socket.
    It also sends OSC messages to connected OSC clients.
    """

    def __init__(self, net, port, max_connections, unix_socket_path):
        """
        Initialize the Tcp2UnixOscServer.

        :param tcp_bind_addr: The address to bind the TCP server to.
        :param tcp_port: The port to bind the TCP server to.
        :param unix_socket_path: The path to the Unix socket to forward data to.
        """
        self.net = net
        self.port = port
        self.max_connections = max_connections
        self.unix_socket_path = unix_socket_path
        self.tcp_server_socket = None
        self.alive = False
        self.threads = []  # List to keep track of threads
        self.osc_clients = []  # List to keep track of OSC clients

    def _listen(self):
        # Create a TCP server socket
        self.tcp_server_socket = socket.socket(
            socket.AF_INET, socket.SOCK_STREAM)
        # Ensure the port is not in TIME_WAIT state
        self.tcp_server_socket.setsockopt(
            socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_server_socket.bind((self.net, self.port))
        self.tcp_server_socket.listen(self.max_connections)

        logging.info("TCP server listening on %s:%s", self.net, self.port)

    def _start_thread(self, target, args=()):
        """
        Start a new thread.

        :param target: The target function for the thread.
        :param args: The arguments for the target function.
        """
        thread = threading.Thread(target=target, args=args)
        thread.start()
        self.threads.append(thread)

    def start(self):
        """
        Start the TCP server.
        """
        self.alive = True
        self._start_thread(self._run_server)

    def _run_server(self):
        """
        Run the TCP server.
        """
        self._listen()
        with self.tcp_server_socket:
            logging.info("TCP server listening on %s:%s",
                         self.net, self.port)
            try:
                while self.alive:
                    self.tcp_server_socket.settimeout(1)
                    try:
                        client_socket, client_address = self.tcp_server_socket.accept()
                        self._start_thread(
                            self._handle_osc_client, (client_socket, client_address))
                    except socket.timeout:
                        continue
            except Exception as e:
                logging.error("Error: %s", e)
            finally:
                self.tcp_server_socket.shutdown(socket.SHUT_RDWR)
        logging.info("TCP Server stopped.")

    def _handle_osc_client(self, client_socket: socket, client_address):
        """
        Handle a TCP client connection.

        :param client_socket: The client socket.
        :param client_address: The client address.
        """
        with client_socket, socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as unix_client_socket:
            logging.info("Accepted connection from %s", client_address)
            osc = OSCClient(client_address[0], 8080)
            self.osc_clients.append(osc)
            try:
                unix_client_socket.connect(self.unix_socket_path)
                last_part = b''
                while self.alive:
                    client_socket.settimeout(1)
                    try:
                        data = client_socket.recv(1024*1024)
                        if not data:
                            break
                        data_parts = data.split(b'\xc0')
                        if data_parts[0]:
                            unix_client_socket.sendall(
                                last_part+data_parts[0])
                            last_part = b''
                        for part in data_parts[1:-1]:
                            if part:
                                print(f"   part:{part}")
                                unix_client_socket.sendall(part)
                        if data_parts[:-1]:
                            print(f"   last_part:{last_part}")
                            last_part = data_parts[-1]
                    except socket.timeout:
                        continue
            except Exception as e:
                logging.exception("Error handling client: %s", e)
            finally:
                self.osc_clients.remove(osc)
        logging.info("TCP Client %s stopped.", client_address)

    def stop(self):
        """
        Stop the TCP server.
        """
        self.alive = False
        for thread in self.threads:
            thread.join()
        logging.info("All TCP Server threads stopped.")

    def send_to_clients(self, address, values):
        """
        Send an OSC message to all connected OSC clients.

        :param address: The OSC address.
        :param values: The OSC values.
        """
        for c in self.osc_clients:
            logging.info("Send: {%s: %s}", address, values)
            c.send_message(address, values)
