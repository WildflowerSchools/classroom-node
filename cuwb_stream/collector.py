from datetime import datetime
import logging
import os
import socket

import cdp


POSITION_V3 = 0x0135
ACCELEROMETER_V3 = 0x017A
GYROSCOPE_V3 = 0x017B
MAGNETOMETER_V3 = 0x017C
PRESSURE_V2 = 0x013C
QUATERNION_V3 = 0x0178
TEMPERATURE_V2 = 0x013E
DEVICE_NAMES = 0x013F
HARDWARE_STATUS_V2 = 0x0138
ANCHOR_HEALTH_V5 = 0x014A
NETWORK_TIME_MAPPING_V1 = 0x015A
DEVICE_ACTIVITY_STATE = 0x0137
DISTANCE_V2 = 0x0127

MAX_TIMESTAMP_REFRESH_DELAY = (
    60  # seconds before we lose confidence in our interpolated real time value
)


DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")


def get_local_ip(routable_ip="8.8.8.8"):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect((routable_ip, 80))
    ip = s.getsockname()[0]
    s.close()
    return ip


class CUWBCollector:
    def __init__(self, ip, port, route_ip, timeout=None):
        self.ip = ip
        if self.ip is None:
            self.ip = os.getenv("CUWB_SOCKET_IP", "0.0.0.0")

        self.port = port
        if self.port is None:
            self.port = os.getenv("CUWB_SOCKET_PORT", "7667")
        self.port = int(self.port)

        self.route_ip = route_ip
        if self.route_ip is None:
            self.route_ip = get_local_ip(os.getenv("CUWB_ROUTABLE_IP", "8.8.8.8"))

        self.listen_socket = None
        self.timeout = timeout

    def start(self):
        if not self.listen_socket:
            self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.listen_socket.bind((self.ip, self.port))
            if self.timeout:
                self.listen_socket.settimeout(self.timeout)
            try:
                self.listen_socket.setsockopt(
                    socket.SOL_IP,
                    socket.IP_ADD_MEMBERSHIP,
                    socket.inet_aton(self.ip) + socket.inet_aton(self.route_ip),
                )
            except socket.error:
                logging.warning(
                    "Failed connecting to socket through remote IP, falling back to a non-routed local connection"
                )

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, _type, value, traceback):
        self.listen_socket.close()
        self.listen_socket = None

    def extract_data_items(
        self,
        socket_read_time,
        data_item_type,
        type_name,
        cdp_packet,
        fields,
        debug=False,
    ):
        for item in cdp_packet.data_items_by_type.get(data_item_type, []):
            if debug:
                logging.warning(
                    f"Logging {type_name}: Definition: {item.definition} - Full Item: {item}"
                )

            timestamp = socket_read_time

            data = {
                "socket_read_time": socket_read_time,
                "timestamp": timestamp,
                "type": type_name,
            }
            for field in fields:
                if hasattr(item, field):
                    data[field] = getattr(item, field)
                    if field in ["serial_number", "serial_number_1", "serial_number_2"]:
                        data[field] = str(data[field])
                    if field == "bad_paired_anchors":
                        data[field] = ",".join([str(di) for di in data[field]])

            yield data

    def __iter__(self):
        self.start()

        while True:
            socket_read_time = None

            try:
                data, _ = self.listen_socket.recvfrom(65535)

                socket_read_time = datetime.utcnow()
                cdp_packet = cdp.CDP(data)
            except ValueError:
                logging.error("Failed parsing socket content")
                yield None
            except socket.timeout:
                logging.error("Socket timed out")
                return

            logging.info(f"Packet received at: {socket_read_time}")

            fields = [
                "serial_number",
                "network_time",
                "x",
                "y",
                "z",
                "scale",
            ]
            for item in self.extract_data_items(
                socket_read_time,
                ACCELEROMETER_V3,
                "accelerometer",
                cdp_packet,
                fields,
                debug=DEBUG,
            ):
                yield item
            for item in self.extract_data_items(
                socket_read_time,
                GYROSCOPE_V3,
                "gyroscope",
                cdp_packet,
                fields,
                debug=DEBUG,
            ):
                yield item
            for item in self.extract_data_items(
                socket_read_time,
                MAGNETOMETER_V3,
                "magnetometer",
                cdp_packet,
                fields,
                debug=DEBUG,
            ):
                yield item

            fields = [
                "serial_number",
                "network_time",
                "x",
                "y",
                "z",
                "w",
                "quaternion_type",
                "quality"
            ]
            for item in self.extract_data_items(
                socket_read_time,
                QUATERNION_V3,
                "quaternion",
                cdp_packet,
                fields,
                debug=DEBUG,
            ):
                yield item

            for item in self.extract_data_items(
                socket_read_time,
                PRESSURE_V2,
                "pressure",
                cdp_packet,
                ["serial_number", "network_time", "pressure", "scale"],
                debug=DEBUG,
            ):
                yield item

            for item in self.extract_data_items(
                socket_read_time,
                TEMPERATURE_V2,
                "temperature",
                cdp_packet,
                ["serial_number", "network_time", "temperature", "scale"],
                debug=DEBUG,
            ):
                yield item

            for item in self.extract_data_items(
                socket_read_time,
                DEVICE_NAMES,
                "names",
                cdp_packet,
                ["serial_number", "name"],
                debug=DEBUG,
            ):
                yield item

            fields = [
                "serial_number",
                "network_time",
                "x",
                "y",
                "z",
                "anchor_count",
                "quality",
                "flags",
                "smoothing",
            ]
            for item in self.extract_data_items(
                socket_read_time,
                POSITION_V3,
                "position",
                cdp_packet,
                fields,
                debug=DEBUG,
            ):
                yield item

            fields = [
                "serial_number",
                "memory",
                "flags",
                "minutes_remaining",
                "battery_percentage",
                "temperature",
                "processor_usage",
            ]
            for item in self.extract_data_items(
                socket_read_time,
                HARDWARE_STATUS_V2,
                "status",
                cdp_packet,
                fields,
                debug=DEBUG,
            ):
                yield item

            fields = [
                "serial_number",
                "interface_id",
                "ticks_reported",
                "timed_rxs_reported",
                "beacons_reported",
                "beacons_discarded",
                "beacons_late",
                "average_quality",
                "report_period",
                "interanchor_comms_error_code",
                "bad_paired_anchors",
            ]
            for item in self.extract_data_items(
                socket_read_time,
                ANCHOR_HEALTH_V5,
                "anchor_health",
                cdp_packet,
                fields,
                debug=DEBUG,
            ):
                yield item

            fields = [
                "serial_number",
                "interface_id",
                "x",
                "y",
                "z",
                "role_id",
                "connectivity_state",
                "synchronization_state",
            ]
            for item in self.extract_data_items(
                socket_read_time,
                DEVICE_ACTIVITY_STATE,
                "device_activity_state",
                cdp_packet,
                fields,
                debug=DEBUG,
            ):
                yield item

            fields = [
                "serial_number_1",
                "serial_number_2",
                "interface_id_1",
                "interface_id_2",
                "rx_timestamp",
                "distance",
                "quality",
            ]
            for item in self.extract_data_items(
                socket_read_time,
                DISTANCE_V2,
                "distance",
                cdp_packet,
                fields,
                debug=DEBUG,
            ):
                yield item


def network_time_to_seconds(ut):
    return float(ut) * 15.65 / (1e12)
