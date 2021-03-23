from datetime import datetime
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
            #self.listen_socket.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton(self.ip) + socket.inet_aton(self.interface))

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, type, value, traceback):
        self.listen_socket.close()
        self.listen_socket = None

    def extract_data_items(self, pkt_time, data_item_type, type_name, cdp_packet, fields, debug=False):
        for item in cdp_packet.data_items_by_type.get(data_item_type, []):
            if debug:
                print(item.definition)
                print(item)
            data = {
                'timestamp': pkt_time,
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
        while True:
            try:
                data, address = self.listen_socket.recvfrom(65536)  # 2^16 is the maximum size of a CDP packet
                cdp_packet = cdp.CDP(data)
            except ValueError:
                logging.error("Failed parsing socket content")
                continue

            pkt_time = datetime.utcnow()
            fields = [
                'serial_number',
                'network_time',
                'x',
                'y',
                'z',
                'scale',
            ]
            for item in self.extract_data_items(pkt_time, ACCELEROMETER_V2, 'accelerometer', cdp_packet, fields):
                yield item
            for item in self.extract_data_items(pkt_time, GYROSCOPE_V2, 'gyroscope', cdp_packet, fields):
                yield item
            for item in self.extract_data_items(pkt_time, MAGNETOMETER_V2, 'magnetometer', cdp_packet, fields):
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
            for item in self.extract_data_items(pkt_time, QUATERNION_V2, 'quaternion', cdp_packet, fields):
                yield item
            for item in self.extract_data_items(pkt_time, PRESSURE_V2, 'pressure', cdp_packet, ['serial_number', 'network_time', 'pressure', 'scale']):
                yield item
            for item in self.extract_data_items(pkt_time, TEMPERATURE_V2, 'temperature', cdp_packet, ['serial_number', 'network_time', 'temperature', 'scale']):
                yield item
            for item in self.extract_data_items(pkt_time, DEVICE_NAMES, 'names', cdp_packet, ['serial_number', 'name']):
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
            for item in self.extract_data_items(pkt_time, POSITION_V3, 'position', cdp_packet, fields):
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
            for item in self.extract_data_items(pkt_time, HARDWARE_STATUS_V2, 'status', cdp_packet, fields):
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
            for item in self.extract_data_items(pkt_time, ANCHOR_HEALTH_V5, 'anchor_health', cdp_packet, fields):
                yield item


def parse_time(ut):
    ts = float(ut) * 15.65 / (10e12)
    return datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
