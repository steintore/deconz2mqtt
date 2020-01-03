import logging
import sys

nameId = {}
idName = {
    "lights": {},
    "sensors": {},
    "groups": {}
}
etags = {}
mqtt_client = None
http_client = None
ws_client = None

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
