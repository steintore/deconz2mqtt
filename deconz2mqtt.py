import logging
from datetime import datetime
import os
import sys
import json
import configparser
import urllib3
import requests
import paho.mqtt.client as mqtt
import websocket
try:
    import thread
except ImportError:
    import _thread as thread
import time
import schedule
import threading

config_file = 'default.cfg'
mqtt_cfg = 'MQTT'
api_cfg = 'API'
bri_max = 255.0
nameId = {}
idName = {
    "lights": {},
    "sensors": {},
    "groups": {}
}
etags = {}
client = None

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logging.info("Startup deconz2mqtt:" + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
config_file_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), config_file)

parser = configparser.ConfigParser()
if os.path.exists(config_file_path):
    parser.read(config_file)
    logging.info("Loaded config file " + config_file_path)
    mqtt_host = parser.get(mqtt_cfg, 'host')
    mqtt_port = parser.getint(mqtt_cfg, 'port')
    mqtt_username = parser.get(mqtt_cfg, 'username')
    mqtt_password = parser.get(mqtt_cfg, 'password')
    mqtt_control_topic = parser.get(mqtt_cfg, 'control_topic')
    mqtt_status_topic = parser.get(mqtt_cfg, 'status_topic')
    GET_UPDATE_INTERVAL = parser.getint(api_cfg, 'update_interval_min')
    api_key = parser.get(api_cfg, 'key')
    api_host = parser.get(api_cfg, 'host')
    api_port = parser.getint(api_cfg, 'port')
    api_url = 'http://{}:{}/api/{}/'.format(api_host, api_port, api_key)
    log_level = parser.get('CONFIG', 'loglevel')
    if log_level != 'INFO':
        logging.info("Changing loglevel from INFO to {}".format(log_level))
        logging.basicConfig(stream=sys.stdout, level=log_level)
else:
    logging.error("ERROR: Config file not found " + config_file_path)
    quit()


def connect_ws():
    websocket.enableTrace(True)
    ws = websocket.WebSocketApp("ws://{}:8080".format(api_host),
                                on_message=on_message_ws,
                                on_error=on_error_ws,
                                on_close=on_close_ws)
    ws.on_open = on_open
    ws.run_forever()


def on_open(ws):
    def run(*args):
        while True:
            ws.send("ping")
            time.sleep(30)
    thread.start_new_thread(run, ())


def on_message_ws(ws, message):
    logging.debug("on_message_ws: {}".format(str(message)))
    json_payload = json.loads(message)
    item_type = json_payload["r"]
    if item_type in ['scenes']:
        return
    item_id = json_payload["id"]
    item_name = idName[item_type].get(item_id, None)
    if item_name is None:
        return
    _state = json_payload["state"]
    logging.debug("id: {}, name: {}, topic: deconz/status/{}/{} - state: {}".format(item_id, item_name, item_type, item_name, _state))
    for key in _state:
        mqtt_publish(item_type, item_name, convert_state_value(key, _state[key]), key)


def on_error_ws(ws, error):
    logging.error(error)


def on_close_ws(ws):
    logging.info("### closed ###")


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    logging.info("Connected to MQTT host " + mqtt_host + " with result code " + str(rc))
    logging.info("Subscribing to api control topic: " + mqtt_control_topic)
    client.subscribe(mqtt_control_topic + "/#")
    logging.info("Publishing to api status topic: " + mqtt_status_topic)
    client.publish(mqtt_status_topic, "MQTT connected")


def on_message(client, userdata, msg):
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
    new_state = convert_state_value(action, msg.payload)
    try:
        url = api_url + "{}/{}/{}".format(item_type, item_id, item_set_state_type)
        action = 'ct' if action == 'cti' else action
        payload = json.dumps({action: new_state})
        logging.debug("put to url: '{}' with payload: {}".format(url, payload))
        res = requests.put(url, data=payload)
        logging.debug("{}, put to url: '{}' with payload: {}".format(res.text, url, payload))
    except urllib3.HTTPError as err:
        logging.error("Failed to fetch data from api {}".format(err))
    #get_latest_data()


def convert_state_value(valueType, value):
    logging.debug("convert_state_value called with values: {}, {}".format(valueType, value))
    if value == False or value == True:
        new_state = 'ON' if value == 'True' else 'OFF'
    else:
        new_state = value in ['True', 'true', 't', 'on', 'ON'] if valueType in ['on', 'reachable', 'status', 'any_on', 'all_on'] else value
    new_state = int(new_state) if valueType in ['bri', 'ct', 'sat', 'hue', 'cti'] else new_state
    if valueType in ['bri', 'sat']:
        new_state = int(round(float(new_state) / 100, 2) * 255)
    if valueType in ['ct', 'cti']:
        new_state = int(round(float(new_state) / 100, 2) * (500 - 153) + 153)
    # TODO Handle HUE / CT values
    return new_state


def get_latest_data():
    get_api_response("lights", etags.get("lights", "0"))
    get_api_response("groups", etags.get("groups", "0"))
    get_api_response("sensors", etags.get('sensors', "0"))


def get_api_response(endpoint_type, etag=None):
    logging.debug("Fetching api response for: " + endpoint_type + " with url: " + api_url + " and etag: " + etag)
    try:
        response = requests.get(
            api_url + endpoint_type,
            headers={'If-None-Match': etag}
        )
        if response.status_code == 304:
            logging.debug("Nothing changed on server")
            return
        logging.debug("Headers from response is: {}".format(response.headers["eTag"]))
        json_response = response.json()
        etags[endpoint_type] = response.headers["eTag"]

        for key in json_response:
            logging.debug('key {}, {}'.format(key, json_response[key]))
            name = json_response[key]['name'].replace(" ", "").lower()
            nameId[name] = key
            idName[endpoint_type][key] = name
            state_ = json_response[key]['state']
            if endpoint_type == 'lights':
                parse_state_and_publish(endpoint_type, json_response, key, name, state_)
            elif endpoint_type == 'groups':
                action = json_response[key]['action']
                parse_state_and_publish(endpoint_type, json_response, key, name, action)
            elif endpoint_type == 'sensors':
                parse_sensor_and_publish(json_response[key], key, name)
    except urllib3.HTTPError as err:
        logging.error("Failed to fetch json_response from api {}".format(err))

def parse_sensor_and_publish(json_response, key, name):
    config_ = json_response['config']
    state_ = json_response['state']
    if 'battery' in config_:
        mqtt_publish('sensors', name, int(0 if config_['battery'] is None else config_['battery']), "battery")
    if 'buttonevent' in state_:
        mqtt_publish('sensors', name, state_['buttonevent'], "event")
    if 'lastupdated' in state_:
        mqtt_publish('sensors', name, state_['lastupdated'], "lastupdated")
    if 'reachable' in config_:
        mqtt_publish('sensors', name, 'ON' if config_['reachable'] else 'OFF', "reachable")

def parse_state_and_publish(endpoint_type, json_response, key, name, state_):
    state = 'ON' if state_['on'] else 'OFF'
    mqtt_publish(endpoint_type, name, state)
    if state_.get('bri', None) is not None:
        bri = int(round(state_.get('bri', bri_max) / bri_max, 2) * 100)
        mqtt_publish(endpoint_type, name, bri, "brightness")
    ct = state_.get('ct', None)
    if ct is not None:
        ct_min = json_response[key].get('ctmin', 0)
        ct_max = json_response[key].get('ctmax', 100)
        ct_percent = int(round(float(ct - ct_min) / (ct_max - ct_min), 2) * 100)
        mqtt_publish(endpoint_type, name, ct_percent, "color_temperature")


def mqtt_publish(type, name, state, status='status'):
    topic = mqtt_status_topic + "/{}/{}/{}".format(type, name.lower(), status)
    logging.info("Publishing: {}/{}".format(topic, state))
    client.publish(topic, state, retain=True)


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.username_pw_set(mqtt_username, mqtt_password)
client.connect(mqtt_host, mqtt_port, 60)
client.publish(mqtt_status_topic, "Connecting to MQTT host " + mqtt_host)
client.loop_start()
#mqtt_thread = threading.Thread(target=client.loop_forever)
ws_thread = threading.Thread(target=connect_ws)
#mqtt_thread.start()
#logging.info("MQTT-thread started...")
ws_thread.start()
logging.info("WS-thread started...")

get_latest_data()
logging.info("Fetched latest data...")

# Then schedule
if GET_UPDATE_INTERVAL and GET_UPDATE_INTERVAL >= 1:
    logging.info("Schedule API update every {} minutes".format(GET_UPDATE_INTERVAL))
    schedule.every(int(GET_UPDATE_INTERVAL)).minutes.do(get_latest_data)
    while True:
        schedule.run_pending()
        time.sleep(1)
