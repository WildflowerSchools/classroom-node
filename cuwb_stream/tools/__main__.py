import uuid

import click

from apscheduler.schedulers.background import BackgroundScheduler
from cuwb_stream.collector import CUWBCollector
from cuwb_stream.network import CUWBNetwork
from cuwb_stream.tools.snooplogg import UWBConnectionSnoop


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
    database_connection = UWBConnectionSnoop()

    uwb_network = CUWBNetwork(host=network_ip, port=network_port)
    network_name = uwb_network.get_networks()[0]['name']
    def capture_network_details():
        devices = uwb_network.get_devices(network_name=network_name)
        settings = uwb_network.get_settings(network_name=network_name)

        database_connection.write_uwb_network_message(
            object_id=uuid.uuid4().hex, data=devices, msg_type="network_devices"
        )
        database_connection.write_uwb_network_message(
            object_id=uuid.uuid4().hex, data=settings, msg_type="network_settings"
        )

    capture_network_details()

    scheduler = BackgroundScheduler()
    scheduler.add_job(capture_network_details, 'interval', minutes=1)
    scheduler.start()

    try:
        with CUWBCollector(ip=socket_ip, port=socket_port, route_ip=socket_route_ip) as collector:
            for bit in collector:
                if bit:
                    database_connection.write_uwb_socket_message(
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
        cuwb_network.ensure_network_is_running(name)
    elif action == "stop":
        cuwb_network.ensure_network_is_stopped(name)


if __name__ == "__main__":
    main()
