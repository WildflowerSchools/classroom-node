from cuwb_stream.collector import CUWBCollector
from cuwb_stream.tools.__main__ import get_local_ip

with CUWBCollector(
        ip="0.0.0.0",
        port=7667,
        interface=get_local_ip()) as collector:
    print("Launching...")
    for bit in collector:
        pass