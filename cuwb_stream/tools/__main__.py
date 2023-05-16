import uuid

import click

from apscheduler.schedulers.background import BackgroundScheduler
from cuwb_stream.collector import CUWBCollector
from cuwb_stream.network import CUWBNetwork
from cuwb_stream.tools.uwb_message_logger import UWBMessageLogger


@click.group()
def main():
    pass


@main.command()
@click.option(
    "--network-ip",
    help="IP for the CUWB network. (defaults to CUWB_NETWORK_IP env or 0.0.0.0)",
)
@click.option(
    "--network-port",
    help="Port for the CUWB network. (defaults to CUWB_SOCKET_PORT env or 5000)",
)
@click.option(
    "--socket-ip",
    help="Socket ip for the CUWB network. (defaults to CUWB_SOCKET_IP env or 239.255.76.67)",
)
@click.option(
    "--socket-port",
    help="Socket port for the CUWB network. (defaults to CUWB_SOCKET_PORT env or 7667)",
)
@click.option(
    "--socket-route-ip",
    help="IP that the interface should route to. (defaults to CUWB_ROUTABLE_IP env or 8.8.8.8)",
)
def collect(
    network_ip=None,
    network_port=None,
    socket_ip=None,
    socket_port=None,
    socket_route_ip=None,
):
    uwb_message_logger = UWBMessageLogger()

    uwb_network = CUWBNetwork(host=network_ip, port=network_port)

    network_name = uwb_network.get_networks()[0]['name']
    uwb_network.ensure_network_is_running(network_name=network_name)

    def capture_network_details():
        devices = uwb_network.get_devices(network_name=network_name)
        settings = uwb_network.get_settings(network_name=network_name)

        for device_data in devices:
            device_firmware_versions_list = device_data.get('firmware_versions', [])
            device_firmware_version_dict = next(filter(lambda fv: fv.get('image_type', '') == 'firmware', device_firmware_versions_list), {})
            device_data['firmware_version'] = device_firmware_version_dict.get('version_string', None)
            device_data['firmware_sha'] = device_firmware_version_dict.get('sha', None)

            uwb_message_logger.write_uwb_network_message(
                object_id=device_data['serial_number'], data={'device_data': device_data}, msg_type="network_devices"
            )

        uwb_message_logger.write_uwb_network_message(
            object_id=uuid.uuid4().hex, data={'setting_data': settings}, msg_type="network_settings"
        )
    capture_network_details()

    scheduler = BackgroundScheduler()
    scheduler.add_job(capture_network_details, 'interval', minutes=1)
    scheduler.start()

    try:
        with CUWBCollector(ip=socket_ip, port=socket_port, route_ip=socket_route_ip) as collector:
            for bit in collector:
                if bit:
                    uwb_message_logger.write_uwb_socket_message(
                        object_id=bit.get("serial_number", uuid.uuid4().hex), data=bit
                    )
    except SystemExit:
        scheduler.shutdown()


@main.command()
@click.option("--name", help="name of the network")
@click.option("--action", help="start or stop")
def network(name, action):
    cuwb_network = CUWBNetwork()
    if action == "start":
        cuwb_network.ensure_network_is_running(network_name=name)
    elif action == "stop":
        cuwb_network.ensure_network_is_stopped(network_name=name)


if __name__ == "__main__":
    main()
