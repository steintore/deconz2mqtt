import json
import time

from deconz2mqtt import conversion, utils

try:
    import thread
except ImportError:
    import _thread as thread

import websocket
from deconz2mqtt.utils import logging as logging


class ws:

    def __init__(self, host, port="8080"):
        self.ws_url = "ws://{}:{}".format(host, port)

    def connect_ws(self):
        websocket.enableTrace(True)
        ws = websocket.WebSocketApp(self.ws_url,
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
    item_name = utils.idName[item_type].get(item_id, None)
    if item_name is None:
        return
    _state = json_payload["state"]
    logging.debug(
        "id: {}, name: {}, topic: deconz/status/{}/{} - state: {}".format(item_id, item_name, item_type, item_name,
                                                                          _state))
    for key in _state:
        utils.mqtt_client.publish(item_type, item_name, conversion.convert_state_value_to_percent(key, _state[key]), key)


def on_error_ws(ws, error):
    logging.error(error)


def on_close_ws(ws):
    logging.info("### closed ###")