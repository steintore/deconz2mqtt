import json
import os

import paho.mqtt.client as mqtt
import requests
import urllib3

from deconz2mqtt.conversion import convert_state_percent_to_value
from deconz2mqtt.utils import logging as logging


def on_message(userdata, msg):
    global nameId
    logging.info("onMessage: " + msg.topic + " " + str(msg.payload))
    topic, action = os.path.split(msg.topic)
    topics = topic.split('/')
    item_name = topics[3]
    item_id = nameId.get(item_name, None)
    logging.debug("Item name is: " + item_name + " item id: {} - {}".format(nameId, item_id))
    if item_id is None:
        logging.error("Could not find item id of item: {}".format(item_name))
        return
    item_type = topics[2]
    item_set_state_type = 'state' if item_type == 'lights' else 'action'
    new_state = convert_state_percent_to_value(action, msg.payload)
    try:
        url = api_url + "{}/{}/{}".format(item_type, item_id, item_set_state_type)
        action = 'ct' if action == 'cti' else action
        payload = json.dumps({action: new_state})
        logging.debug("put to url: '{}' with payload: {}".format(url, payload))
        res = requests.put(url, data=payload)
        logging.debug("{}, put to url: '{}' with payload: {}".format(res.text, url, payload))
    except urllib3.HTTPError as err:
        logging.error("Failed to fetch data from api {}".format(err))
    # get_latest_data()


mqtt_cfg = 'MQTT'


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
        self.client.on_message = on_message
        self.client.username_pw_set(self.mqtt_username, self.mqtt_password)
        self.client.connect(self.mqtt_host, self.mqtt_port, 60)
        self.client.publish(self.mqtt_status_topic, "Connecting to MQTT host " + self.mqtt_host)
        self.client.loop_start()

    def publish(self, type, name, state, status='status'):
        topic = self.mqtt_status_topic + "/{}/{}/{}".format(type, name.lower(), status)
        logging.info("Publishing: {}/{}".format(topic, state))
        self.client.publish(topic, state, retain=True)

    # The callback for when the client receives a CONNACK response from the server.
    def on_connect(self, client, userdata, flags, rc):
        logging.info("Connected to MQTT host " + self.mqtt_host + " with result code " + str(
            rc) + " subscribing to: " + self.mqtt_control_topic + " publishing to: " + self.mqtt_status_topic)
        client.subscribe(self.mqtt_control_topic + "/#")
        client.publish(self.mqtt_status_topic, "MQTT connected")
