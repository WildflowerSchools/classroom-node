from fabric import Connection


PASSWORD = "animalflowerpot16candles"


hosts = [
    {"ip": "10.22.0.62", "name": "wildflower-tech-camera-5"},
    {"ip": "10.22.0.30", "name": "wildflower-tech-camera-11"},
    {"ip": "10.22.0.34", "name": "wildflower-tech-camera-2"},
    {"ip": "10.22.0.38", "name": "wildflower-tech-camera-3"},
    {"ip": "10.22.0.42", "name": "wildflower-tech-camera-4"},
    {"ip": "10.22.0.14", "name": "wildflower-tech-camera-6"},
    {"ip": "10.22.0.46", "name": "wildflower-tech-camera-7"},
    {"ip": "10.22.0.50", "name": "wildflower-tech-camera-8"},
]

for host in hosts:
    c = Connection(host["ip"], user="wildflowertech", connect_kwargs={
        "password": PASSWORD,
    })
    try:
        c.sudo('reboot', password=PASSWORD)
    except:
        pass
