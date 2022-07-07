import io
import yaml

from fabric import Connection

PASSWORD = "animalflowerpot16candles"

hosts = [
    "192.168.1.9",
    "192.168.1.8",
    "192.168.1.13",
    "192.168.1.12",
    "192.168.1.18",
    "192.168.1.46",
    "192.168.1.47",
    "192.168.1.17",
    "192.168.1.10",
    "192.168.1.45",
]

for host in hosts:
    try:
        c = Connection(host, user="wildflowertech", connect_kwargs={
            "password": PASSWORD,
        })
        print("=" * 90)
        print("starting %s" % host)
        print("=" * 90)
        c.sudo('systemctl enable systemd-resolved.service', password=PASSWORD)
        c.sudo('systemctl restart systemd-resolved.service', password=PASSWORD)

    except Exception as e:
        print(e)
        pass
