import time
import datetime
import socket
import threading
import traceback

import bottle
# from bottle import route, run, abort
from ruuvitag_sensor.ruuvi import RuuviTagSensor

import ruuvitag_sensor.log
ruuvitag_sensor.log.enable_console()


# 2019-12-18 20:20:56 : pip install bleson ruuvitag_sensor bottle
# 2021-01-13 15:16:01 also : yay -S bluez-hcitool

# 2021-01-14 19:13:04 TODO history? save last x sensor data?
# 2021-01-14 20:29:21 TODO also how and when to update and send to ruuvi-gateway

SENSORS_CACHE = {}
SENSORS_STATS = {}
HOSTNAME = socket.gethostname()
MAC_NAMES = {
    'F1:2F:DF:A6:54:2D': 'a',
    'D3:7B:2A:86:C1:8F': 'b',
    'C1:BC:27:F5:05:D5': 'c',
    'D1:77:35:6E:E9:6C': 'd',
    'C1:BB:41:CE:37:D2': 'e',
    'D1:45:50:9C:34:C3': 'f',
}

sensor_lock = threading.Lock()

class RuuviThread(threading.Thread):
    """ asdf """

    def run(self):
        """ run the ruuvi get_datas """
        # RuuviTagSensor.get_datas(self.cb, [])
        RuuviTagSensor.get_datas(self.cb, [], bt_device='hci1')

    def cb(self, dat):
        """ the callback function for handling sensor data """
        try:
            mac = dat[0]
            data = dat[1]
            ruuvi_name = mac.replace(':', '').lower()
            ruuvi_name = MAC_NAMES.get(mac, ruuvi_name)
            now = '{0:%Y-%m-%d %H:%M:%S%z}'.format(datetime.datetime.now())

            if mac not in SENSORS_STATS:
                SENSORS_STATS[mac] = {
                    'name': ruuvi_name,
                    'count': 0,
                    'first': now,
                    'last': now,
                }
            SENSORS_STATS[mac]['count'] += 1
            SENSORS_STATS[mac]['last'] = now

            ruuvi_station_format = {
                "id": mac,
                "name": ruuvi_name,
                "deviceId": HOSTNAME,
                # "longitude": resp['location']['longitude'],
                # "latitude": resp['location']['latitude'],
                # "accuracy": resp['location']['accuracy'],
                "temperature": data['temperature'],
                "humidity": data['humidity'],
                "pressure": data['pressure'] * 100,  # pascal(Pa) to hectopascal(hPa)
                "accelX": data['acceleration_x'] / 1000,
                "accelY": data['acceleration_y'] / 1000,
                "accelZ": data['acceleration_z'] / 1000,
                "movementCounter": data.get('movement_counter', 0),
                "measurementSequenceNumber": data.get('measurement_sequence_number', 0),
                "rssi": data['rssi'],
                "txPower": data.get('tx_power', 0),
                "updateAt": now,
                "voltage": data['battery'] / 1000,  # millivolt to volt
            }
            print(f'{now} [{ruuvi_name}] {ruuvi_station_format["measurementSequenceNumber"]} {ruuvi_station_format["temperature"]}C {ruuvi_station_format["humidity"]}% {ruuvi_station_format["pressure"]}hPa ({ruuvi_station_format["accelX"]} {ruuvi_station_format["accelY"]} {ruuvi_station_format["accelZ"]}) {ruuvi_station_format["voltage"]}v {ruuvi_station_format["movementCounter"]} {ruuvi_station_format["rssi"]}')
            SENSORS_CACHE[mac] = ruuvi_station_format
            # SENSORS_CACHE[ruuvi_name] = ruuvi_station_format
            # dt = '{0:%Y-%m-%d %H:%M:%S}'.format(datetime.datetime.now())
            # print(f'{dt} {macname: <17} {data["temperature"]}C, {data["humidity"]}%, {data["pressure"]}')
        except Exception as err:
            print('whoopsie', err)
            traceback.print_exc()


@bottle.get("/")
def index():
    return {}


@bottle.get("/macs")
def get_macs():
    return SENSORS_CACHE


@bottle.get("/macs/<mac>")
def get_mac(mac):
    resp = {}
    if mac in SENSORS_CACHE:
        resp = SENSORS_CACHE.get(mac, {})
    else:
        # try to find by name
        for _mac, _dat in SENSORS_CACHE.items():
            if _dat.get('name', '') == mac:
                resp = _dat
                break
    return resp


@bottle.get("/stats")
def get_stats():
    return SENSORS_STATS


@bottle.get("/tags")
def get_tags():
    # the format posted to ruuvi gateway
    return {'tags': [tag for mac, tag in SENSORS_CACHE.items()]}


print('starting RuuviThread')
ruuvi_thread = RuuviThread()
ruuvi_thread.start()

print('starting HTTP host')
bottle.run(host="0.0.0.0", port=8881, debug=True)
