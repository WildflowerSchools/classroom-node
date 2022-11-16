from collections import defaultdict
import multiprocessing
import os
import pty
import socket
import subprocess
import time

from cuwb_stream.collector import CUWBCollector
from cuwb_stream.tools.__main__ import get_local_ip


REPO_NAME = os.getenv("REPO_NAME")

cdp_socket_ip = "0.0.0.0"
cdp_socket_port = 7667


def run_collector(message_list):
    try:
        with CUWBCollector(
            ip=cdp_socket_ip, port=cdp_socket_port, interface=get_local_ip(), timeout=2
        ) as collector:
            for msg in collector:
                message_list.append(msg)
    except socket.timeout:
        pass


def test_collector():
    test_dir = os.path.dirname(os.path.realpath(__file__))
    _, tty = pty.openpty()

    # Build the collector
    return_code = subprocess.call(
        ["make", "build-cdp-player", f"REPO_NAME={REPO_NAME}"],
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=f"{test_dir}/..",
    )
    if return_code != 0:
        raise Exception(
            "Unable to build cdp-player container, required to test UWB parsing logic"
        )

    manager = multiprocessing.Manager()
    message_list = manager.list()

    # Start the collector in a bkgd process
    p = multiprocessing.Process(target=run_collector, args=(message_list,))
    p.start()

    # Give the collector plenty of time to startup
    time.sleep(1)

    # Launch the cdp-player to stream data, the collector should capture this
    subprocess.Popen(
        ["make run-cdp-player", f"REPO_NAME={REPO_NAME}"],
        shell=True,
        stdin=tty,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=f"{test_dir}/..",
    )

    # The collector will timeout once it no longer is receiving messages
    p.join()

    assert len(message_list) == 120
    assert message_list[0]["type"] == "device_activity_state"
    assert message_list[0]["serial_number"] == "01:04:062C"

    group_messages = defaultdict(list)
    for message in message_list:
        group_messages[message["type"]].append(message)

    assert len(group_messages["anchor_health"]) == 24
    assert len(group_messages["device_activity_state"]) == 66
    assert len(group_messages["names"]) == 30

    subprocess.Popen(
        ["docker", "stop", "cdp-player"], shell=True, stdin=tty, stdout=tty, stderr=tty
    )
