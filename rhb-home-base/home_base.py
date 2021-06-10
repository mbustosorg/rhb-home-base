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
import serial

import geopy.distance
from digi.xbee.devices import XBeeDevice, RemoteXBeeDevice, XBee64BitAddress

FORMAT = '%(asctime)-15s [%(name)s] %(message)s'
logging.basicConfig(format=FORMAT)
LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

#37.850457333,-122.253884333
BASE_LATITUDE = 37.85
BASE_LONGITUDE = -122.25

PING_PERIOD = datetime.timedelta(seconds=30)
ACK_PERIOD = datetime.timedelta(seconds=15)

in_range = False

teensy_serial = serial.Serial(port='/dev/ttyACM0',
                              baudrate=9600,
                              parity=serial.PARITY_NONE,
                              stopbits=serial.STOPBITS_ONE,
                              bytesize=serial.EIGHTBITS,
                              timeout=0)


def iterate_beacons(base_distance: float):
    """ Send out current tower values """
    teensy_serial.write(str(int(base_distance * 1000.0)).encode('UTF-8'))
    teensy_serial.flush()


def check_teensy_messages():
    """ Check to see if teensy has anything to say """
    teensy_message = teensy_serial.read(100)
    if len(teensy_message):
        LOGGER.info(f'Message from teensy: {teensy_message.decode("UTF-8")}')


if __name__ == '__main__':
    last_ping = datetime.datetime.now()
    last_receipt = datetime.datetime.now()
    #radio = XBeeDevice('/dev/tty.usbserial-AH001572', 9600)
    radio = XBeeDevice('/dev/ttyUSB0', 9600)
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
            distance = geopy.distance.distance(source, target).mi
            LOGGER.info(f'Range: {distance:.2f} miles')
            if not in_range:
                in_range = True
                rate = int(1.0 / distance * 4000)
                tower_values = [rate, rate, rate]
                iterate_beacons(distance)
                LOGGER.info('Mobile platform in range')
        if ((datetime.datetime.now() - last_receipt) > ACK_PERIOD) & in_range:
            in_range = False
            tower_values = [0, 0, 0]
            iterate_beacons(999999.0)
            LOGGER.info('Lost mobile platform')
        check_teensy_messages()
        time.sleep(0.1)


