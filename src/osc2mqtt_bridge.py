"""
A bridge that connects OSC (Open Sound Control) and MQTT (Message Queuing Telemetry Transport)
protocols. It listens for OSC messages and publishes them to an MQTT topic, and vice versa.
"""
import time
import logging
import queue
import shutil
import os
from collections.abc import Iterable
import yaml
from mqtt_handler import MQTTClientHandler
from osc_handler import OSCServerHandler
from simple_thread import SimpleThread
from t2u_osc_server import Tcp2UnixOscServer


class OSC2MQTTBridge:
    """
    A bridge that connects OSC (Open Sound Control) and MQTT (Message Queuing Telemetry Transport)
    protocols. It listens for OSC messages and publishes them to an MQTT topic, and vice versa.
    """

    def __init__(self, config, encoding='utf-8'):
        """
        Initialize the OSC2MQTTBridge with the given configuration.

        :param config: Configuration dictionary containing MQTT and OSC settings.
        :param encoding: Encoding to use for OSC messages.
        """
        self.config = config
        self.encoding = encoding
        self.mqtt_handler = MQTTClientHandler(**config["mqtt"]["connection"])
        self.osc_handler = OSCServerHandler(config["osc"]["unix_socket_path"])
        self.t2u = Tcp2UnixOscServer(**config["osc"])
        self.o2m_task = None
        self.m2o_task = None

    def start(self):
        """
        Start the OSC2MQTTBridge. This includes starting the OSC server, TCP to Unix OSC server,
        connecting to the MQTT broker, and starting the message handling loops.
        """
        self.osc_handler.start()
        self.t2u.start()
        topic_cmnd = self.config["mqtt"]["topics"]["subscribe"]
        topic_stat = self.config["mqtt"]["topics"]["publish"]
        try:
            self.mqtt_handler.connect()
            self.mqtt_handler.subscribe_json(topic_cmnd + "/#")
        except Exception as e:
            logging.error("Failed to start OSC2MQTTBridge: %s", str(e))
            logging.error("Trace", e)
            raise SystemExit(
                "Exiting due to failure in starting OSC2MQTTBridge.") from e
        self.mqtt_handler.start()
        self.o2m_task = SimpleThread(self._o2m_loop, args=(topic_stat,))
        self.m2o_task = SimpleThread(self._m2o_loop, args=(topic_cmnd,))

    def stop(self):
        """
        Stop the OSC2MQTTBridge. This includes stopping the message handling loops, MQTT handler,
        TCP to Unix OSC server, and OSC server.
        """
        if self.m2o_task:
            self.m2o_task.stop()
        if self.o2m_task:
            self.o2m_task.stop()
        self.mqtt_handler.stop()
        self.t2u.stop()
        self.osc_handler.stop()

    def _o2m_loop(self, topic_stat):
        """
        Loop to handle OSC messages and publish them to the MQTT topic.

        :param topic_stat: The MQTT topic prefix for publishing OSC messages.
        """
        try:
            address, values = self.osc_handler.osc_buffer.get(timeout=1)
            address = address.decode(self.encoding)
            topic = topic_stat + address
            message = values[0] if len(values) == 1 else values
            logging.info("OSC->MQTT: {%s: %s}", topic, message)
            self.mqtt_handler.publish_json(topic, message)
        except queue.Empty:
            pass

    def _m2o_loop(self, topic_cmnd, auto_send_zero=True):
        """
        Loop to handle MQTT messages and send them as OSC messages.

        :param topic_cmnd: The MQTT topic prefix for subscribing to MQTT messages.
        :param auto_send_zero: Whether to automatically send a [0.0] message after a [1.0] message.
        """
        try:
            topic, message = self.mqtt_handler.mqtt_buffer.get(timeout=1)
            logging.info("MQTT->OSC: {%s: %s}", topic, message)
            prefix = topic_cmnd
            if topic.startswith(prefix):
                address = topic[len(prefix):]
                b_addr = address.encode('utf-8')
                values = message if isinstance(
                    message, Iterable) else [message]
                self.t2u.send_to_clients(b_addr, values)
                if auto_send_zero and message == 1.0:
                    time.sleep(0.1)
                    self.t2u.send_to_clients(b_addr, [0.0])
        except queue.Empty:
            pass


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # if "config/config.yaml" does not exist
    if not os.path.exists("config/config.yaml"):
        # copy config.yaml.example to config.yaml
        shutil.copy("config.yaml.example", "config/config.yaml")
        logging.info(
            "Copied config.yaml.example to config/config.yaml. Please edit the configuration file before running the bridge.")
        # exit the program
        raise SystemExit(
            "Exiting due to missing configuration file. Please edit config/config.yaml.")

    with open("config/config.yaml", "r", encoding='utf-8') as config_file:
        yaml_config = yaml.safe_load(config_file)
    
    # verify that the config file is valid
    crt=yaml_config["mqtt"]["connection"].get("ca_certs", None)
    if crt and not os.path.exists(crt):
        logging.error("CA certificate file %s does not exist.", crt)
        raise SystemExit("Exiting due to missing CA certificate file.")

    bridge = OSC2MQTTBridge(yaml_config)

    try:
        bridge.start()
        while True:
            time.sleep(0.5)
    except SystemExit as e:
        logging.info(str(e))
    except KeyboardInterrupt:
        logging.info("Shutting down...")
    finally:
        bridge.stop()
