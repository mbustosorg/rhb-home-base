"""
    Copyright (C) 2021 Mauricio Bustos (m@bustos.org)
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.
    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.
    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import datetime
import logging
import time
import random
from typing import List

import Adafruit_PCA9685
import geopy.distance
from digi.xbee.devices import XBeeDevice, RemoteXBeeDevice, XBee64BitAddress

FORMAT = '%(asctime)-15s [%(name)s] %(message)s'
logging.basicConfig(format=FORMAT)
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

BASE_LATITUDE = 35.88
BASE_LONGITUDE = -122.222

PING_PERIOD = datetime.timedelta(seconds=30)
ACK_PERIOD = datetime.timedelta(seconds=15)

pwm = Adafruit_PCA9685.PCA9685()

in_range = False

BEACON_MIN = 0
BEACON_MAX = 4000
tower_values: List[int] = [0, random(50), random(50)]


def iterate_beacons():
    for index, value in enumerate(tower_values):
        value -= 5
        if value < BEACON_MIN:
            value = BEACON_MAX
        pwm.set_pwm(index, 0, value)
        tower_values[index] = value


if __name__ == '__main__':
    last_ping = datetime.datetime.now()
    last_receipt = datetime.datetime.now()
    radio = XBeeDevice('/dev/tty.usbserial-AH001572', 9600)
    radio.open()

    while True:
        if (datetime.datetime.now() - last_ping) > PING_PERIOD:
            mobile_platform = RemoteXBeeDevice(radio, XBee64BitAddress.from_hex_string('0013A20041CB7786'))
            radio.send_data_async(mobile_platform, str(BASE_LATITUDE) + ',' + str(BASE_LONGITUDE))
            LOGGER.info('PING')
            last_ping = datetime.datetime.now()
        message = radio.read_data()
        if message:
            last_receipt = datetime.datetime.now()
            coords = message.data.decode().split(',')
            LOGGER.info(f'Remote coordinates: {message.data.decode()}')
            target = (float(coords[0]), float(coords[1]))
            source = (BASE_LATITUDE, BASE_LONGITUDE)
            LOGGER.info(f'Range: {geopy.distance.distance(source, target).mi:.2f} miles')
            if not in_range:
                in_range = True
                LOGGER.info('Mobile platform in range')
        if ((datetime.datetime.now() - last_receipt) > ACK_PERIOD) & in_range:
            in_range = False
            LOGGER.info('Lost mobile platform')
        iterate_beacons()
        time.sleep(0.1)


