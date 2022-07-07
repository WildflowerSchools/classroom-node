from fabric import Connection


PASSWORD = "animalflowerpot16candles"


hosts = [
    {"ip": "10.22.0.82", "name": "dev-1"},
    {"ip": "10.22.0.86", "name": "dev-2"},
    {"ip": "10.22.0.94", "name": "dev-4"},
    {"ip": "10.22.0.66", "name": "wildflower-tech-camera-12"},
]

for host in hosts:
    c = Connection(host["ip"], user="wildflowertech", connect_kwargs={
        "password": PASSWORD,
    })
    try:
        c.sudo('shutdown 0', password=PASSWORD)
    except:
        pass
