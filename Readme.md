# deconz2mqtt

This is a Python utility that translates the [deCONZ rest api](https://dresden-elektronik.github.io/deconz-rest-doc/) to MQTT messages.
Will later be using WebSockets for fetching changes on the fly that are published
to MQTT.
There is also a full update of all items every x minutes, to make sure we have the last updated values.

The utility is connecting to the [deCONZ rest api](https://dresden-elektronik.github.io/deconz-rest-doc/) 


# TODO

- [ ] Implement proper WebSocket
- [ ] Send alive-messages over MQTT to tell the receiver the app is online
- [ ] Scenes
- [ ] Write the readme
- [ ] Make a service
- [ ] Tests https://realpython.com/python-testing/
- [ ] OpenHAB examples and details about how to use it


## Installation

To get this working you must have deCONZ running on a computer and the deCONZ rest api in place

Clone this repo and install the dependencies
```shell script
$ git clone this.repo 
$ cd this.repo
$ cp default.template.cfg default.cfg
```

- Update the new file `default.cfg`with all the correct values
- Get a new api_key to insert if you do not have one


### Install other python libs

`pip3 install -r requirements.txt`

*pip3 may require `sudo`*


### This is work is inspired by 
[leaf-python-mqtt](https://github.com/glynhudson/leaf-python-mqtt) and [deconz-mqtt](https://github.com/xibriz/deconz-mqtt)


## Run script as system service

### Create Systemd service

Create systemd service, assuming repo was cloned to `/home/pi` folder on a RaspberryPi, adjust paths if needed

`$ sudo ln -s /home/pi/deconz2mqtt/deconz2mqtt.service /etc/systemd/system/deconz2mqtt.service`

Set permissions:

`$ sudo chmod 644  /etc/systemd/system/deconz2mqtt.service`

Reload systemd then enable the service at startup:

```
$ sudo systemctl daemon-reload
$ sudo systemctl enable deconz2mqtt.service
$ sudo systemctl start deconz2mqtt.service
```

Check service status and view log snippet with:

`$ sudo systemctl status deconz2mqtt.service`

To view more lines of logs add `nXX` where XX is the number of lines e.g. to view 50 lines of logs

`$ sudo systemctl status deconz2mqtt.service -n50`

Start, stop and restart with:

```
$ sudo systemctl start deconz2mqtt.service
$ sudo systemctl stop deconz2mqtt.service
$ sudo systemctl restart deconz2mqtt.service
```
