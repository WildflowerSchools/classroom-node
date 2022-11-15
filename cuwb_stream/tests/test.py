import multiprocessing
import sys

import pytest
import socket
import threading
import time

from cuwb_stream.collector import CUWBCollector
from cuwb_stream.tools.__main__ import get_local_ip


local_ip = "172.17.0.1"
local_port = 7667


def read_cdplog():
    with open("./data/cdplog-2022-11-08.00", "rb") as infile:
        data = infile.read(8000)
        while data:
            yield data
            data = infile.read(8000)

    print("DIE")
    sys.exit()


def socket_service(ip, port):
    server = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
    #server.bind((local_ip, local_port))
    #server.listen(5)

    for data in read_cdplog():
        #server.sendto(bytes("HI", encoding='utf-8'), (ip, port))
        server.sendto(data, (ip, port))
        time.sleep(.05)
        # conn, addr = server.accept()
        # msg = str(conn.recv(1024),'utf8')
        # c.send(bytes('GOT: {0}'.format(msg),'utf8')
        # c.close()


@pytest.fixture
def socket_server():
    process = multiprocessing.Process(target=socket_service, args=(local_ip, local_port, ), daemon=True)
    process.start()
    time.sleep(1)
    yield
    process.kill()


def test_collector():

    #server_thread = threading.Thread(target=server_service, args=(local_ip, local_port, ))

    with CUWBCollector(
            ip="0.0.0.0",
            port=7667,
            interface=get_local_ip()) as collector:
        for bit in collector:
            pass

    assert True