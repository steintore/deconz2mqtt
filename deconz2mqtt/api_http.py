import requests
from urllib3.exceptions import HTTPError

from deconz2mqtt import utils
from deconz2mqtt.utils import logging as logging


class Http:
    def __init__(self, api_key, api_host, api_port):
        self.url = 'http://{}:{}/api/{}/'.format(api_host, api_port, api_key)

    def get_api_response(self, endpoint_type, etag=None):
        logging.debug("Fetching api response for: " + endpoint_type + " with url: " + self.url + "/" + endpoint_type + " and etag: " + etag)
        try:
            response = requests.get(
                self.url + endpoint_type,
                headers={'If-None-Match': etag}
            )
            if response.status_code == 304:
                logging.debug("Nothing changed on server")
                return
            logging.debug("Headers from response is: {}".format(response.headers["eTag"]))
            json_response = response.json()
            utils.etags[endpoint_type] = response.headers["eTag"]

            for key in json_response:
                logging.debug('get_api_response: key: {}, value: {}'.format(key, json_response[key]))
                name = json_response[key]['name'].replace(" ", "").lower()
                utils.nameId[name] = key
                utils.idName[endpoint_type][key] = name
                state_ = json_response[key]['state']
                if endpoint_type == 'lights':
                    utils.mqtt_client.parse_state_and_publish(endpoint_type, json_response, key, name, state_)
                elif endpoint_type == 'groups':
                    action = json_response[key]['action']
                    utils.mqtt_client.parse_state_and_publish(endpoint_type, json_response, key, name, action)
                elif endpoint_type == 'sensors':
                    utils.mqtt_client.parse_sensor_and_publish(json_response[key], name)
        except HTTPError as err:
            logging.error("Failed to fetch json_response from api {}".format(err))

    def send_to_api(self, item_type, item_id, item_set_state_type, payload):
        try:
            url = self.url + "{}/{}/{}".format(item_type, item_id, item_set_state_type)
            logging.debug("put to url: '{}' with payload: {}".format(url, payload))
            res = requests.put(url, data=payload)
            logging.debug("{}, put to url: '{}' with payload: {}".format(res.text, url, payload))
        except HTTPError as err:
            logging.error("Failed to fetch data from api {}".format(err))
