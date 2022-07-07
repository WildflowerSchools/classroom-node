import io
import yaml

from fabric import Connection

PASSWORD = "animalflowerpot16candles"

hosts = [
    "192.168.0.14",
    "192.168.0.15",
    "192.168.0.17",
    "192.168.0.18",
    "192.168.0.21",
    "192.168.0.22",
    "192.168.0.24",
    "192.168.0.27",
    "192.168.0.28",
    "192.168.0.30",
    "192.168.0.32",
    "192.168.0.37",
    "192.168.0.111",
    "192.168.0.139",
    "192.168.0.146",
    "192.168.0.148",
    "192.168.0.149",
    "192.168.0.150",
    "192.168.0.151",
    "192.168.0.220",
    "192.168.0.221",
    "192.168.0.222",
    "192.168.0.223",
    "192.168.0.224",
]

for host in hosts:
    try:
        c = Connection(host, user="wildflowertech", connect_kwargs={
            "password": PASSWORD,
        })
        print("=" * 90)
        print("starting %s" % host)
        print("=" * 90)
        config = c.run('cat /boot/wildflower-config.yml', hide='both').stdout.strip()
        print(yaml.load(config)["hostname"])
        # c.sudo("sed 's/TBD/http:\\/\\/wildflower-tech.org/g' /etc/systemd/system/wf-shoe.service", password=PASSWORD, warn=True)
        # c.sudo('systemctl restart  wf-shoe.service', password=PASSWORD, warn=True)
    except Exception as e:
        print(e)
        pass
