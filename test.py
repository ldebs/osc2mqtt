from simple_thread import SimpleThread
import queue
import json
import logging
import time
import os
from collections.abc import Iterable
from oscpy.server import OSCThreadServer
from oscpy.client import OSCClient
from paho.mqtt import client as mqtt
from t2u_osc_server import Tcp2UnixOscServer

logging.basicConfig(level=logging.INFO)

# Initialize a FIFO buffer using queue.Queue
osc_buffer = queue.Queue()
mqtt_buffer = queue.Queue()


def mqtt_conn():
    broker = 'mqtt.ldebs.org'
    port = 8883
    client_id = 'osc-to-mqtt'
    username = 'mqtt'
    password = '622cb2de7309a2ca904cb9926bd9a19d'

    def on_connect(client, userdata, flags, rc, properties):
        if rc == 0:
            logging.info("Connected to MQTT Broker %s:%d as %s",
                         broker, port, client_id)
        else:
            msg = f"Failed to connect, return code {rc}"
            logging.error(msg)
            raise ConnectionError(msg)

    def on_disconnect(client, userdata, rc):
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

    client = mqtt.Client(client_id=client_id,
                         callback_api_version=mqtt.CallbackAPIVersion.VERSION2)

    client.username_pw_set(username, password)
    client.tls_set(ca_certs='/etc/ssl/certs/ca-certificates.crt')
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.connect(broker, port)
    return client


def publish(client, msg_dict: dict):
    for topic, obj in msg_dict.items():
        msg = json.dumps(obj, cls=BytesEncoder)
        info = client.publish(topic, msg, 2)
        if info.rc == mqtt.MQTT_ERR_SUCCESS:
            logging.info("OSC->MQTT:{%s:%s}", topic, msg)
        else:
            msg = "OSC->MQTT:FAIL=%d:{%s:%s}" % (info.rc, topic, msg)
            logging.error(msg)
            raise IOError(msg)


def subscribe(client, topic):
    def on_message(client, userdata, msg):
        mqtt_buffer.put((msg.topic, json.loads(msg.payload.decode('utf_8'))))

    client.on_message = on_message
    rc, mid = client.subscribe(topic, 2)
    if rc == mqtt.MQTT_ERR_SUCCESS:
        logging.info(
            "Subscribed with success to %s, message id is %d", topic, mid)
    else:
        msg = f"Failed to subscribe to topic {topic}, reason code {rc}"
        logging.error(msg)
        raise ConnectionError(msg)


class BytesEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, bytes):
            return o.decode("utf-8")
        else:
            return super().default(o)


def osc_server(unix_socket) -> OSCThreadServer:
    def cb(address, *values):
        osc_buffer.put((address, values))
    osc = OSCThreadServer(default_handler=cb)
    osc.listen(address=unix_socket, default=True, family='unix')
    logging.info(f"Listen OSC messages from {unix_socket})")
    return osc


def o2m_run(client, mqtt_topic_pub):
    try:
        address, values = osc_buffer.get(timeout=1)
        address = address.decode('utf-8')
        topic = mqtt_topic_pub + address
        if len(values) == 1:
            msg = values[0]
        else:
            msg = values
        msg_dict = {topic: msg}
        publish(client, msg_dict)
    except queue.Empty:
        pass


def m2o_run(client, mqtt_topic_sub, osc_send_message):
    try:
        topic, payload = mqtt_buffer.get(timeout=1)
        logging.info("MQTT->OSC:{%s:%s}", topic, payload)
        prefix = "osc/cmnd/openSC"
        if topic.startswith(prefix):
            address = topic[len(prefix):]
            if isinstance(payload, Iterable):
                values = payload
            else:
                values = [payload]
            b_addr = address.encode('utf-8')
            osc_send_message(b_addr, values)
            if payload == 1.0:
                time.sleep(0.1)
                osc_send_message(b_addr, [0.0])
    except queue.Empty:
        pass


def main():
    unix_socket = '/tmp/osc.sock'
    if os.path.exists(unix_socket):
        os.remove(unix_socket)
    osc = osc_server(unix_socket=unix_socket)
    t2u = Tcp2UnixOscServer("0.0.0.0", 57272, unix_socket)
    t2u.start()
    mqtt_stat = 'osc/stat'
    mqtt_cmnd = 'osc/cmnd/#'

    client = mqtt_conn()
    subscribe(client, mqtt_cmnd)
    client.loop_start()
    o2m = SimpleThread(o2m_run, (client, mqtt_stat))
    m2o = SimpleThread(m2o_run, (client, mqtt_cmnd, t2u.send_to_clients))

    try:
        while True:
            try:
                time.sleep(0.5)
            except KeyboardInterrupt:
                logging.info("Bye bye!")
                break
    finally:
        m2o.stop()
        o2m.stop()
        t2u.stop()
        client.loop_stop()
        osc.stop()


if __name__ == "__main__":
    main()
