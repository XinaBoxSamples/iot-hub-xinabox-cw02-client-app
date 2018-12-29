# Azure IoT Controlled publish period
import streams
import json
from xinabox.sl06 import sl06
from wireless import wifi

simulated = False

if simulated == False:
    # SL06 instance
    SL06 = sl06.SL06(I2C0)
    # configure SL06
    SL06.init()
    # enable SL06 for light sensing
    SL06.enableLightSensor()

# choose a wifi chip supporting secure sockets
from espressif.esp32net import esp32wifi as wifi_driver

import requests
# import azure iot module
from azure.iot import iot

# import helpers functions to easily load keys and device configuration
import helpers

# DEVICE KEY FILE MUST BE PLACED INSIDE PROJECT FOLDER
new_resource('private.base64.key')
# set device configuration inside this json file
new_resource('device.conf.json')

# define a callback for twin updates
def twin_callback(twin, version):
    global publish_period
    print('new twin version:', version)
    print('requested publish period:', twin['publish_period'])
    publish_period = twin['publish_period']
    return {'publish_period': publish_period}

# define a callback for cloud to device messages
def bound_callback(msg, properties):
    print('received msg:', msg)
    print('with properties:', properties)

# define a callback for a cloud direct method
def send_something(method_payload):
    return (0,{'something': random(0,10)})

streams.serial()
wifi_driver.auto_init()

# use the wifi interface to link to your Access Point
# change network name, security and password as needed
print("Establishing Link...")
try:
    # FOR THIS EXAMPLE TO WORK, "Network-Name" AND "Wifi-Password" MUST BE SET
    # TO MATCH YOUR ACTUAL NETWORK CONFIGURATION
    wifi.link("Network-Name",wifi.WIFI_WPA2,"Wifi-Password")
    print("Link Established")
except Exception as e:
    print("ooops, something wrong while linking :(", e)
    while True:
        sleep(1000)

pkey = helpers.load_key('private.base64.key')
device_conf = helpers.load_device_conf()
publish_period = 5000 # publish period in ms
sample_th = 5

# choose an appropriate way to get a valid timestamp (may be available through hardware RTC)
def get_timestamp():
    user_agent = {"user-agent": "curl/7.56.0"}
    return json.loads(requests.get('http://now.httpbin.org', headers=user_agent).content)['now']['epoch']

# create an azure iot device instance, connect to mqtt broker, set twin callback and start mqtt reception loop
device = iot.Device(device_conf['hub_id'], device_conf['device_id'], device_conf['api_version'], pkey, get_timestamp)
device.mqtt.connect()

device.on_bound(bound_callback)
device.on_method('get', send_something)
device.on_twin_update(twin_callback)
device.mqtt.loop()

while True:
    if simulated == False:
        ambient_light = SL06.getAmbientLight()  # read the the ambient light level
        print('Ambient Light Level: ', ambient_light)
        device.publish_event({'asample': ambient_light}, {'above_th': ambient_light > sample_th})
    else:
        ambient_light = random(0, 100) # create random value to report
        print('Ambient Light Level: ', ambient_light)
        device.publish_event({'asample': ambient_light}, {'above_th': ambient_light > sample_th})
        
    sleep(publish_period)

