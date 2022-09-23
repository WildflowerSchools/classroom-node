from datetime import datetime
import os
import socket

import cdp
import logging


POSITION_V3 = 0x0135
ACCELEROMETER_V2 = 0x0139
GYROSCOPE_V2 = 0x013A
MAGNETOMETER_V2 = 0x013B
PRESSURE_V2 = 0x013C
QUATERNION_V2 = 0x013D
TEMPERATURE_V2 = 0x013E
DEVICE_NAMES = 0x013F
HARDWARE_STATUS_V2 = 0x0138
ANCHOR_HEALTH_V5 = 0x014A
NETWORK_TIME_MAPPING_V1 = 0x015A

MAX_TIMESTAMP_REFRESH_DELAY = 60  # seconds before we lose confidence in our interpolated real time value


DEBUG = os.getenv('DEBUG', "False").lower() in ('true', '1', 't')

class CUWBNetworkTimeMapping:
    def __init__(self,
                 last_real_time_previous,
                 last_real_time_current,
                 last_network_time_previous,
                 last_network_time_current):
        self.last_real_time_previous = last_real_time_previous
        self.last_real_time_current = last_real_time_current
        self.last_network_time_previous = last_network_time_previous
        self.last_network_time_current = last_network_time_current

    def rt_per_nt(self):
        return (self.last_real_time_current - self.last_real_time_previous) /\
               (self.last_network_time_current - self.last_network_time_previous)

    def interpolate_real_time_from_network_time(self, network_time):
        """
        Determine real time from network time

        :param network_time: As picoseconds
        :return: Real time as microseconds
        """
        return self.last_real_time_current +\
               ((network_time - self.last_network_time_current) * self.rt_per_nt())

    @staticmethod
    def real_time_as_date_time(real_time):
        return datetime.utcfromtimestamp(real_time/1e6)


class CUWBCollector:

    def __init__(self, ip, port, interface):
        self.ip = ip
        self.port = port
        self.interface = interface
        self.listen_socket = None

    def start(self):
        if not self.listen_socket:
            self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.listen_socket.bind((self.ip, self.port))
            try:
                self.listen_socket.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton(self.ip) + socket.inet_aton(self.interface))
            except:
                logging.error("Failed connecting to socket through remote IP, falling back to a non-routed local connection")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, type, value, traceback):
        self.listen_socket.close()
        self.listen_socket = None

    def extract_data_items(self, socket_read_time, data_item_type, type_name, cdp_packet, fields, last_time_mapping: CUWBNetworkTimeMapping=None, debug=False):
        for item in cdp_packet.data_items_by_type.get(data_item_type, []):
            if debug:
                logging.warning("Logging {}: Definition: {} - Full Item: {}".format(type_name, item.definition, item))

            timestamp = None
            if 'network_time' in fields:
                network_time = getattr(item, 'network_time')

                if last_time_mapping is None:
                    logging.warning("Skipping '{}': Data item contains 'network_time', but a CUWBNetworkTime has not yet been interpolated".format(type_name))
                    return

                # 4/27/21 - Stop excluding instances when last synced network time is a more recent timestamp
                #           than the timestamp in the IMU record
                # if network_time < last_time_mapping.last_network_time_current:
                #     logging.warning("Skipping '{}': Data item's 'network_time' is less than the last recorded CUWBNetworkTime. Network has likely reset. Waiting for CUWBNetworkTime to refresh.".format(type_name))
                #     return

                seconds_since_refresh = network_time_to_seconds(network_time - last_time_mapping.last_network_time_current)
                if seconds_since_refresh > MAX_TIMESTAMP_REFRESH_DELAY:
                    logging.warning("Skipping '{}': Data item contains 'network_time', but CUWBNetworkTime hasn't been refreshed for {} seconds. Waiting for CUWBNetworkTime refresh.".format(type_name, seconds_since_refresh))
                    return

                interpolated_real_time = last_time_mapping.interpolate_real_time_from_network_time(network_time)
                timestamp = CUWBNetworkTimeMapping.real_time_as_date_time(interpolated_real_time)

            data = {
                'socket_read_time': socket_read_time,
                'timestamp': timestamp,
                'type': type_name,
            }
            for field in fields:
                if hasattr(item, field):
                    data[field] = getattr(item, field)
                    if field == 'serial_number':
                        data[field] = str(data[field])
                    if field == 'bad_paired_anchors':
                        data[field] = ','.join([str(di) for di in data[field]])

            yield data

    def __iter__(self):
        self.start()

        last_time_mapping = None
        while True:
            try:
                data, address = self.listen_socket.recvfrom(65535)  # 2^16 is the maximum size of a CDP packet
                socket_read_time = datetime.utcnow()
                cdp_packet = cdp.CDP(data)
            except ValueError:
                logging.error("Failed parsing socket content")
                continue

            logging.info("Packet received at: {}".format(socket_read_time))

            fields = [
                'real_time_previous',
                'real_time_current',
                'network_time_previous',
                'network_time_current']
            for item in self.extract_data_items(socket_read_time, NETWORK_TIME_MAPPING_V1, 'network_time', cdp_packet, fields, last_time_mapping=last_time_mapping, debug=DEBUG):
                # Resync network time
                last_time_mapping = CUWBNetworkTimeMapping(last_real_time_previous=item['real_time_previous'],
                                                           last_real_time_current=item['real_time_current'],
                                                           last_network_time_previous=item['network_time_previous'],
                                                           last_network_time_current=item['network_time_current'])
                yield item

            fields = [
                'serial_number',
                'network_time',
                'x',
                'y',
                'z',
                'scale',
            ]
            for item in self.extract_data_items(socket_read_time, ACCELEROMETER_V2, 'accelerometer', cdp_packet, fields, last_time_mapping=last_time_mapping, debug=DEBUG):
                yield item
            for item in self.extract_data_items(socket_read_time, GYROSCOPE_V2, 'gyroscope', cdp_packet, fields, last_time_mapping=last_time_mapping, debug=DEBUG):
                yield item
            for item in self.extract_data_items(socket_read_time, MAGNETOMETER_V2, 'magnetometer', cdp_packet, fields, last_time_mapping=last_time_mapping, debug=DEBUG):
                yield item

            fields = [
                'serial_number',
                'network_time',
                'x',
                'y',
                'z',
                'w',
                'quaternion_type',
            ]
            for item in self.extract_data_items(socket_read_time, QUATERNION_V2, 'quaternion', cdp_packet, fields, last_time_mapping=last_time_mapping, debug=DEBUG):
                yield item

            for item in self.extract_data_items(socket_read_time, PRESSURE_V2, 'pressure', cdp_packet, ['serial_number', 'network_time', 'pressure', 'scale'], last_time_mapping=last_time_mapping, debug=DEBUG):
                yield item

                for item in self.extract_data_items(socket_read_time, TEMPERATURE_V2, 'temperature', cdp_packet, ['serial_number', 'network_time', 'temperature', 'scale'], last_time_mapping=last_time_mapping, debug=DEBUG):
                yield item

            for item in self.extract_data_items(socket_read_time, DEVICE_NAMES, 'names', cdp_packet, ['serial_number', 'name'], last_time_mapping=last_time_mapping, debug=DEBUG):
                yield item

            fields = [
                'serial_number',
                'network_time',
                'x',
                'y',
                'z',
                'anchor_count',
                'quality',
                'flags',
                'smoothing',
            ]
            for item in self.extract_data_items(socket_read_time, POSITION_V3, 'position', cdp_packet, fields, last_time_mapping=last_time_mapping, debug=DEBUG):
                yield item

            fields = [
                'serial_number',
                'memory',
                'flags',
                'minutes_remaining',
                'battery_percentage',
                'temperature',
                'processor_usage',
            ]
            for item in self.extract_data_items(socket_read_time, HARDWARE_STATUS_V2, 'status', cdp_packet, fields, last_time_mapping=last_time_mapping, debug=DEBUG):
                yield item

            fields = [
                'serial_number',
                'interface_id',
                'ticks_reported',
                'timed_rxs_reported',
                'beacons_reported',
                'beacons_discarded',
                'beacons_late',
                'average_quality',
                'report_period',
                'interanchor_comms_error_code',
                'bad_paired_anchors',
            ]
            for item in self.extract_data_items(socket_read_time, ANCHOR_HEALTH_V5, 'anchor_health', cdp_packet, fields, last_time_mapping=last_time_mapping, debug=DEBUG):
                yield item


def network_time_to_seconds(ut):
    return float(ut) * 15.65 / (1e12)
