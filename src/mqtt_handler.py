"""
This module provides an MQTT client handler for connecting to an MQTT broker,
publishing and subscribing to topics, and handling JSON messages.
"""

import json
import logging
import time
import queue
from paho.mqtt import client as mqtt


class MQTTClientHandler:
    """
    A class to handle MQTT client operations including connecting to a broker,
    publishing and subscribing to topics, and handling JSON messages.
    """

    class BytesEncoder(json.JSONEncoder):
        """
        Custom JSON encoder to handle bytes objects.
        """
        encoding = 'utf-8'

        def default(self, o):
            """
            Override the default method to handle bytes objects.
            """
            if isinstance(o, bytes):
                return o.decode(self.encoding)
            else:
                return super().default(o)

    def __init__(self, broker, port, client_id, username, password, ca_certs, encoding='utf-8'):
        """
        Initialize the MQTTClientHandler.

        :param broker: The MQTT broker address.
        :param port: The port to connect to on the broker.
        :param client_id: The client ID to use when connecting to the broker.
        :param username: The username for authentication.
        :param password: The password for authentication.
        :param ca_certs: Path to the CA certificate file.
        :param encoding: The encoding to use for messages (default is 'utf-8').
        """
        self.broker = broker
        self.port = port
        self.client_id = client_id
        self.username = username
        self.password = password
        self.ca_certs = ca_certs
        self.encoding = encoding
        self.BytesEncoder.encoding = encoding
        self.client = mqtt.Client(client_id=self.client_id,
                                  callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        self.client.username_pw_set(self.username, self.password)
        self.client.tls_set(ca_certs=self.ca_certs)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.mqtt_buffer = queue.Queue()

    def _on_connect(self, client, userdata, flags, rc, properties):
        """
        Callback for when the client connects to the broker.

        :param client: The client instance.
        :param userdata: User data of any type.
        :param flags: Response flags sent by the broker.
        :param rc: The connection result code.
        :param properties: The MQTT properties.
        """
        if rc == 0:
            logging.info("Connected to MQTT Broker %s:%d as %s",
                         self.broker, self.port, self.client_id)
        else:
            msg = f"Failed to connect, return code {rc}"
            logging.error(msg)
            raise ConnectionError(msg)

    def _on_disconnect(self, client, userdata, rc):
        """
        Callback for when the client disconnects from the broker.

        :param client: The client instance.
        :param userdata: User data of any type.
        :param rc: The disconnection result code.
        """
        logging.info("Disconnected with result code: %d", rc)
        count, delay = 0, 1
        while count < 12:
            logging.info("Reconnecting in %d seconds...", delay)
            time.sleep(delay)
            try:
                client.reconnect()
                logging.info("Reconnected successfully!")
                return
            except Exception as err:
                logging.error("Reconnect failed: %s", err)
            delay *= 2
            delay = min(delay, 60)
            count += 1
        msg = f"Reconnect failed after {count} attempts"
        logging.error(msg)
        raise ConnectionError(msg)

    def _on_json_message(self, client, userdata, msg):
        """
        Callback for when a message is received on a subscribed topic.

        :param client: The client instance.
        :param userdata: User data of any type.
        :param msg: The received message.
        """
        self.mqtt_buffer.put(
            (msg.topic, json.loads(msg.payload.decode(self.encoding))))

    def connect(self):
        """
        Connect to the MQTT broker.
        """
        self.client.connect(self.broker, self.port)

    def publish_json(self, topic, message, qos=2, retain=False):
        """
        Publish a JSON message to a topic.

        :param topic: The topic to publish to.
        :param message: The message to publish.
        :param qos: The quality of service level (default is 2).
        :param retain: Whether to retain the message (default is False).
        """
        message = json.dumps(message, cls=self.BytesEncoder)
        info = self.client.publish(topic, message, qos, retain)
        if info.rc == mqtt.MQTT_ERR_SUCCESS:
            logging.info("Published to MQTT: {%s: %s}", topic, message)
        else:
            msg = f"Failed to publish to topic {topic}, reason code {info.rc}"
            logging.error(msg)
            raise IOError(msg)

    def subscribe_json(self, topic, qos=2):
        """
        Subscribe to a topic and handle JSON messages.

        :param topic: The topic to subscribe to.
        :param qos: The quality of service level (default is 2).
        """
        self.client.on_message = self._on_json_message
        rc, mid = self.client.subscribe(topic, qos)
        if rc == mqtt.MQTT_ERR_SUCCESS:
            logging.info(
                "Subscribed to topic %s, message id is %d", topic, mid)
        else:
            msg = f"Failed to subscribe to topic {topic}, reason code {rc}"
            logging.error(msg)
            raise ConnectionError(msg)

    def start(self):
        """
        Start the MQTT client loop.
        """
        self.client.loop_start()

    def stop(self):
        """
        Stop the MQTT client loop.
        """
        self.client.loop_stop()
