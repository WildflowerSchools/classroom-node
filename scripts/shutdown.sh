from fabric import Connection


PASSWORD = "animalflowerpot16candles"

config = '{"master": "192.168.0.13:6443", "token": "K10814ac967e07a5d781d249bb08d26eaa5cd6049099f05250f5d9698f7ddf7515f::node:fa35599a3f7aac5e06c848902035616e"}'

hosts = [
    {"ip": "10.22.0.62", "name": "wildflower-tech-camera-5"},
    # {"ip": "10.22.0.30", "name": "wildflower-tech-camera-11"},
    # {"ip": "10.22.0.34", "name": "wildflower-tech-camera-2"},
    # {"ip": "10.22.0.38", "name": "wildflower-tech-camera-3"},
    # {"ip": "10.22.0.42", "name": "wildflower-tech-camera-4"},
    {"ip": "10.22.0.14", "name": "wildflower-tech-camera-6"},
    # {"ip": "10.22.0.46", "name": "wildflower-tech-camera-7"},
    # {"ip": "10.22.0.50", "name": "wildflower-tech-camera-8"},
]

for host in hosts:
    c = Connection(host["ip"], user="wildflowertech", connect_kwargs={
        "password": PASSWORD,
    })
    print("starting %s" % host['name'])
    print(c.run("date").stdout)
    c.put('k3s-config.json', 'k3s-config.json')
    c.sudo('mv k3s-config.json /usr/lib/wildflower/broadcast/k3s-config.json', password=PASSWORD)
    c.sudo('systemctl restart k3s', password=PASSWORD)
