import os
import socket

import click

from cuwb_stream.collector import CUWBCollector
from cuwb_stream.network import ensure_network_is_running, ensure_network_is_stopped
from cuwb_stream.tools.snooplogg import DatabaseConnectionSnoop


def get_local_ip(routable_ip='8.8.8.8'):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect((routable_ip, 80))
    ip = s.getsockname()[0]
    s.close()
    return ip


@click.group()
@click.pass_context
def main(ctx):
    pass


@main.command()
@click.pass_context
@click.option('--consumer', help='the consumer type, supports `stdout`, `csv`, or `honeycomb` at this time')
@click.option('--environment_name_honeycomb', help='name of the environment in honeycomb, required for using the honeycomb consumer')
@click.option('--path_csv', help='path for csv file output, required for using the csv consumer')
@click.option('--ip', help='Socket ip for the CUWB network. (defaults to CUWB_SOCKET_IP env or 239.255.76.67)')
@click.option('--port', help='Socket port for the CUWB network. (defaults to CUWB_SOCKET_PORT env or 7667)')
@click.option('--route_ip', help='IP that the interface should route to. (defaults to CUWB_SOCKET_PORT env or 8.8.8.8)')
def collect(ctx, consumer, environment_name_honeycomb=None, path_csv=None, ip=None, port=None, route_ip=None):
    if consumer not in ['stdout']:
        raise ValueError('consumer must be `stdout`')

    database_connection = DatabaseConnectionSnoop()

    ip = ip if ip else os.environ.get('CUWB_SOCKET_IP', '0.0.0.0')
    port = port if port else os.environ.get('CUWB_SOCKET_PORT', 7667)
    interface = route_ip if route_ip else get_local_ip(os.environ.get('CUWB_ROUTABLE_IP', '8.8.8.8'))
    with CUWBCollector(ip, int(port), interface) as collector:
        for bit in collector:
            if bit:
                database_connection.write_datapoint_object_time_series(
                    object_id=bit.get("serial_number"),
                    data=bit
                )


@main.command()
@click.pass_context
@click.option('--name', help='name of the network')
@click.option('--action', help='start or stop')
def network(ctx, name, action):
    if action == "start":
        ensure_network_is_running(name)
    elif action == "stop":
        ensure_network_is_stopped(name)


@main.command()
@click.pass_context
@click.option('--file', help='path to the file to upload')
@click.option('--serial_number', help='serial_number for the device')
@click.option('--start', help='starting timestamp')
@click.option('--type', help='type of measurement(s)')
@click.option('--environment_name_honeycomb', help='name of the environment in honeycomb, required for using the honeycomb consumer')
def upload(ctx, environment_name_honeycomb, file, serial_number, start, type):
    from database_connection_honeycomb import DatabaseConnectionHoneycomb
    database_connection = DatabaseConnectionHoneycomb(
        environment_name_honeycomb=environment_name_honeycomb,
        object_type_honeycomb="DEVICE",
        object_id_field_name_honeycomb="serial_number"
    )
    with open(file, 'r') as fp:
        database_connection.write_datapoint_object_time_series(
            timestamp=start,
            object_id=serial_number,
            data=fp.read()
        )


if __name__ == '__main__':
    main()
