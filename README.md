# OSC2MQTT Bridge

**OSC2MQTT Bridge** is a Python-based bridge that connects [OSC (Open Sound Control)](https://opensoundcontrol.stanford.edu/) and [MQTT (Message Queuing Telemetry Transport)](https://mqtt.org/) protocols. It listens for OSC messages and publishes them to an MQTT topic, and vice versa, enabling seamless integration between OSC-enabled devices/applications and MQTT-based systems.

---

## Features

- **Bidirectional Bridge:** Forwards messages from OSC to MQTT and from MQTT to OSC.
- **Unix Socket OSC Server:** Listens for OSC messages on a Unix domain socket.
- **MQTT TLS Support:** Secure connection to MQTT brokers using CA certificates.
- **Docker Support:** Easily build and run the bridge in a containerized environment.
- **Configurable:** All settings are managed via a YAML configuration file.

---

## Quick Start

### Manually download the installer and run
```
wget -O /tmp/setup.sh https://github.com/ldebs/osc2mqtt/raw/refs/heads/master/scripts/setup.sh
bash /tmp/setup.sh
```

### From source

#### 1. Clone the Repository

```bash
git clone https://github.com/ldebs/osc2mqtt.git
cd osc2mqtt
```

#### 2. Configure

- Copy the example configuration:

  ```bash
  mkdir -p docker/config
  cp src/config.yaml.example docker/config/config.yaml
  ```

- Edit `docker/config/config.yaml` to match your MQTT broker and OSC setup.

- If using TLS, place your CA certificate at the path specified in `ca_certs`.

#### 3. Build and Run

##### Manual Docker Build

```bash
./scripts/build.sh
docker run --rm -v $(pwd)/config:/app/config -p 57272:57272 osc2mqtt
```

##### Native (Without Docker)

1. Install dependencies:

   ```bash
   cd src
   pip install -r requirements.txt
   ```

2. Run the bridge:

   ```bash
   python osc2mqtt_bridge.py
   ```

---

## Configuration

Edit `config.yaml`:

```yaml
mqtt:
  connection:
    broker: "mybroker.example.com" # hostname of the MQTT brocker, must match the certificate for TLS
    port: 8883                     # port of the MQTT brocker
    client_id: "osc-to-mqtt"       # Client ID to use to connect
    username: "mqtt_user"          # User name
    password: "mqtt_password"      # Password
    ca_certs: "config/root.crt"    # Root certificate needed to validate the TLS
  topics:
    publish: "osc/stat"            # Topic where to publish messages from OSC
    subscribe: "osc/cmnd/openSC"   # Topic where to listen messages to OSC

osc:
  net: "0.0.0.0"                    # network to listen for OSC tcp connexion
  port: 57272                       # port to listen for OSC tcp connexion
  max_connections: 10               # maximum connections to handle
  unix_socket_path: "/tmp/osc.sock" # internal socket file
```

- **mqtt.connection:** MQTT broker connection details.
- **mqtt.topics:** Topics for publishing and subscribing.
- **osc:** OSC server network and socket settings.

---

## Troubleshooting

- Ensure your MQTT broker is reachable and the credentials are correct.
- If using TLS, verify the CA certificate path.
- Check logs for errors (`docker compose logs` or console output).

---

## License

[![Creative Commons License](https://i.creativecommons.org/l/by-nc-sa/4.0/88x31.png)](http://creativecommons.org/licenses/by-nc-sa/4.0/)
  
**OSC2MQTT** by [ldebs](https://github.com/ldebs) is licensed under a [Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License](http://creativecommons.org/licenses/by-nc-sa/4.0/).

Permissions beyond the scope of this license may be available, contact me.

---

## Contributing

Pull requests and issues are welcome!

Feel free to [buy me a coffee](https://www.buymeacoffee.com/ldebs) ^^

---

## Authors

- [ldebs](https://github.com/ldebs)