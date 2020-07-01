import os

import paho.mqtt.client as mqtt

from deconz2mqtt import conversion, utils
from deconz2mqtt.conversion import convert_state_to_http_payload
from deconz2mqtt.utils import logging as logging


class Mqtt:
    client = None

    def __init__(self, username, password, host, port, status_topic, control_topic):
        self.mqtt_username = username
        self.mqtt_password = password
        self.mqtt_host = host
        self.mqtt_port = port
        self.mqtt_status_topic = status_topic
        self.mqtt_control_topic = control_topic

    def config_and_connect_mqtt(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.username_pw_set(self.mqtt_username, self.mqtt_password)
        self.client.connect(self.mqtt_host, self.mqtt_port, 60)
        self.client.publish(self.mqtt_status_topic, "Connecting to MQTT host " + self.mqtt_host)
        self.client.loop_start()
        logging.info("Connected to MQTT")

    def publish(self, type, name, state, status='status'):
        topic = self.mqtt_status_topic + "/{}/{}/{}".format(type, name.lower(), status)
        logging.info("Publishing: {} state: {}".format(topic, state))
        self.client.publish(topic, state, retain=True)

    # The callback for when the client receives a CONNACK response from the server.
    def on_connect(self, client, userdata, flags, rc):
        logging.info("Connected to MQTT host " + self.mqtt_host + " with result code " + str(
            rc) + " subscribing to: " + self.mqtt_control_topic + " publishing to: " + self.mqtt_status_topic)
        self.client.subscribe(self.mqtt_control_topic + "/#")
        self.client.publish(self.mqtt_status_topic, "MQTT connected")

    def on_message(self, client, userdata, msg):
        logging.info("on_message-1: " + msg.topic + " " + str(msg.payload))
        topic, action = os.path.split(msg.topic)
        topics = topic.split('/')
        item_name = topics[3]
        item_id = utils.nameId.get(item_name, None)
        logging.debug("on_message-2: Item name is: {}, item id: {} - {}".format(item_name, utils.nameId, item_id))
        if item_id is None:
            logging.error("Could not find item id of item: {}".format(item_name))
            return
        item_type = topics[2]
        logging.debug("on_message-3: action: {}, item_type: {}, msg: {}".format(action, item_type, msg))
        item_set_state_type, payload = convert_state_to_http_payload(action, item_type, msg.payload)
        logging.debug("on_message-4: action: {}, item_type: {}, msg: {}, isst: {}, payload: {}".format(action, item_type, msg, item_set_state_type, payload))
        utils.http_client.send_to_api(item_type, item_id, item_set_state_type, payload)

    def parse_state_and_publish(self, endpoint_type, json_response, key, name, state_):
        state = 'ON' if getattr(state_, 'on', None) else 'OFF'
        if state is not None:
            self.publish(endpoint_type, name, state, 'on')

        if state_.get('bri', None) is not None:
            bri = conversion.bri_to_percent(state_.get('bri', conversion.global_bri_max))
            self.publish(endpoint_type, name, bri, 'bri')

        ct = state_.get('ct', None)
        if ct is not None:
            ct_min = json_response[key].get('ctmin', conversion.global_ct_min)
            ct_max = json_response[key].get('ctmax', conversion.global_ct_max)
            ct_percent = conversion.ct_to_percent(ct, ct_min, ct_max)
            self.publish(endpoint_type, name, ct_percent, 'ct')

    def parse_sensor_and_publish(self, json_response, name):
        value_type = 'sensors'
        config_ = json_response['config']
        state_ = json_response['state']
        if 'battery' in config_:
            self.publish(value_type, name, int(0 if config_['battery'] is None else config_['battery']),
                         'battery')
        if 'buttonevent' in state_:
            self.publish(value_type, name, state_['buttonevent'], 'buttonevent')
        if 'lastupdated' in state_:
            self.publish(value_type, name, state_['lastupdated'], 'lastupdated')
        if 'reachable' in config_:
            self.publish(value_type, name, conversion.string_to_on_off(config_['reachable']), 'reachable')
