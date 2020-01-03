import configparser
import json
import os
import sys
from datetime import datetime

import requests
import urllib3
import websocket

from deconz2mqtt import mqtt, conversion
from deconz2mqtt.utils import logging as logging

try:
    import thread
except ImportError:
    import _thread as thread
import time
import schedule
import threading

config_file = './default.cfg'
api_cfg = 'API'
nameId = {}
idName = {
    "lights": {},
    "sensors": {},
    "groups": {}
}
etags = {}
mqtt_client = None

logging.info("Startup deconz2mqtt:" + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
config_file_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), config_file)

parser = configparser.ConfigParser()
if os.path.exists(config_file_path):
    parser.read(config_file)
    logging.info("Loaded config file " + config_file_path)
    mqtt_cfg = mqtt.mqtt_cfg
    mqtt_host = parser.get(mqtt_cfg, 'host')
    mqtt_port = parser.getint(mqtt_cfg, 'port')
    mqtt_username = parser.get(mqtt_cfg, 'username')
    mqtt_password = parser.get(mqtt_cfg, 'password')
    mqtt_control_topic = parser.get(mqtt_cfg, 'control_topic', fallback='deconz/control')
    mqtt_status_topic = parser.get(mqtt_cfg, 'status_topic', fallback='deconz/status')
    mqtt_client = mqtt.Mqtt(mqtt_username, mqtt_password, mqtt_host, mqtt_port, mqtt_status_topic, mqtt_control_topic)

    update_interval_min = parser.getint(api_cfg, 'update_interval_min', fallback=15)

    api_key = parser.get(api_cfg, 'key')
    api_host = parser.get(api_cfg, 'host')
    api_port = parser.getint(api_cfg, 'port')
    api_url = 'http://{}:{}/api/{}/'.format(api_host, api_port, api_key)

    log_level = parser.get('CONFIG', 'loglevel', fallback='INFO')
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
    logging.debug(
        "id: {}, name: {}, topic: deconz/status/{}/{} - state: {}".format(item_id, item_name, item_type, item_name,
                                                                          _state))
    for key in _state:
        mqtt_client.publish(item_type, item_name, conversion.convert_state_value_to_percent(key, _state[key]), key)


def on_error_ws(ws, error):
    logging.error(error)


def on_close_ws(ws):
    logging.info("### closed ###")


def get_latest_data():
    for value_type in ['lights', 'groups', 'sensors']:
        get_api_response(value_type, etags.get(value_type, "0"))


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
                parse_sensor_and_publish(json_response[key], name)
    except urllib3.HTTPError as err:
        logging.error("Failed to fetch json_response from api {}".format(err))


def parse_sensor_and_publish(json_response, name):
    value_type = 'sensors'
    config_ = json_response['config']
    state_ = json_response['state']
    if 'battery' in config_:
        mqtt_client.publish(value_type, name, int(0 if config_['battery'] is None else config_['battery']), "battery")
    if 'buttonevent' in state_:
        mqtt_client.publish(value_type, name, state_['buttonevent'], "event")
    if 'lastupdated' in state_:
        mqtt_client.publish(value_type, name, state_['lastupdated'], "lastupdated")
    if 'reachable' in config_:
        mqtt_client.publish(value_type, name, conversion.string_to_on_off(config_['reachable']), "reachable")


def parse_state_and_publish(endpoint_type, json_response, key, name, state_):
    state = 'ON' if state_['on'] else 'OFF'
    mqtt_client.publish(endpoint_type, name, state)
    if state_.get('bri', None) is not None:
        bri = conversion.bri_to_percent(state_.get('bri', conversion.global_bri_max))
        mqtt_client.publish(endpoint_type, name, bri, "brightness")
    ct = state_.get('ct', None)
    if ct is not None:
        ct_min = json_response[key].get('ctmin', conversion.global_ct_min)
        ct_max = json_response[key].get('ctmax', conversion.global_ct_max)
        ct_percent = conversion.ct_to_percent(ct, ct_min, ct_max)
        mqtt_client.publish(endpoint_type, name, ct_percent, "color_temperature")


mqtt_client.config_and_connect_mqtt()

ws_thread = threading.Thread(target=connect_ws)
ws_thread.start()
logging.info("WS-thread started...")

get_latest_data()
logging.info("Fetched latest data...")

# Then schedule
if update_interval_min and update_interval_min >= 1:
    logging.info("Schedule API update every {} minutes".format(update_interval_min))
    schedule.every(int(update_interval_min)).minutes.do(get_latest_data)
    while True:
        schedule.run_pending()
        time.sleep(1)
