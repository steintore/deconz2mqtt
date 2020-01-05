import configparser
import os
import sys
from datetime import datetime

from deconz2mqtt import mqtt, api_http, utils, ws
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
mqtt_cfg = 'MQTT'

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
    mqtt_control_topic = parser.get(mqtt_cfg, 'control_topic', fallback='deconz/control')
    mqtt_status_topic = parser.get(mqtt_cfg, 'status_topic', fallback='deconz/status')
    utils.mqtt_client = mqtt.Mqtt(mqtt_username, mqtt_password, mqtt_host, mqtt_port, mqtt_status_topic, mqtt_control_topic)

    update_interval_min = parser.getint(api_cfg, 'update_interval_min', fallback=15)

    api_key = parser.get(api_cfg, 'key')
    api_host = parser.get(api_cfg, 'host')
    api_port = parser.getint(api_cfg, 'port')
    utils.http_client = api_http.Http(api_key, api_host, api_port)
    utils.ws_client = ws.ws(api_host, "8080") # TODO Fetch this from API
    log_level = parser.get('CONFIG', 'loglevel', fallback='INFO')
    if log_level != 'INFO':
        logging.info("Changing loglevel from INFO to {}".format(log_level))
        logging.basicConfig(stream=sys.stdout, level=log_level)
else:
    logging.error("ERROR: Config file not found " + config_file_path)
    quit()


def get_latest_data():
    for value_type in ['lights', 'groups', 'sensors']:
        utils.http_client.get_api_response(value_type, utils.etags.get(value_type, "0"))


mqtt_thread = threading.Thread(target=utils.mqtt_client.config_and_connect_mqtt)
ws_thread = threading.Thread(target=utils.ws_client.connect_ws)

mqtt_thread.start()
get_latest_data()
ws_thread.start()
logging.info("WS-thread started...")

logging.info("Fetched latest data...")

# Then schedule
if update_interval_min and update_interval_min >= 1:
    logging.info("Schedule API update every {} minutes".format(update_interval_min))
    schedule.every(int(update_interval_min)).minutes.do(get_latest_data)
    while True:
        schedule.run_pending()
        time.sleep(100)

