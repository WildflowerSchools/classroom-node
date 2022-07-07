from fabric import Connection


PASSWORD = "animalflowerpot16candles"

config = '{"master": "192.168.0.13:6443", "token": "K10814ac967e07a5d781d249bb08d26eaa5cd6049099f05250f5d9698f7ddf7515f::node:fa35599a3f7aac5e06c848902035616e"}'

hosts = [
    {"ip": "192.168.0.27", "name": "wildflower-tech-camera-10", "conf": "camera-10.conf"},
    {"ip": "192.168.0.36", "name": "wildflower-tech-camera-11", "conf": "camera-11.conf"},
    {"ip": "192.168.0.26", "name": "wildflower-tech-camera-2", "conf": "camera-2.conf"},
    {"ip": "192.168.0.23", "name": "wildflower-tech-camera-3", "conf": "camera-3.conf"},
    {"ip": "192.168.0.39", "name": "wildflower-tech-camera-4", "conf": "camera-4.conf"},
    {"ip": "192.168.0.28", "name": "wildflower-tech-camera-6", "conf": "camera-6.conf"},
    {"ip": "192.168.0.37", "name": "wildflower-tech-camera-7", "conf": "camera-7.conf"},
    {"ip": "192.168.0.38", "name": "wildflower-tech-camera-8", "conf": "camera-8.conf"},
]

for host in hosts:
    c = Connection(host["ip"], user="wildflowertech", connect_kwargs={
        "password": PASSWORD,
    })
    print("starting %s" % host['name'])
    print(c.run("date").stdout)
    if c.run('test -f /usr/lib/wildflower/broadcast/k3s-config.json', warn=True).failed:
        c.put('k3s-config.json', 'k3s-config.json')
        c.sudo('mv k3s-config.json /usr/lib/wildflower/broadcast/k3s-config.json', password=PASSWORD)
        c.sudo('systemctl restart k3s', password=PASSWORD)
    print("  updating ovpn config")
    c.put(host['conf'], 'openvpn_client.conf')
    c.sudo('cp openvpn_client.conf /boot/openvpn_client.conf', password=PASSWORD)
    c.sudo('rm openvpn_client.conf', password=PASSWORD)
    c.sudo('systemctl restart openvpn@client', password=PASSWORD)




curl -sL https://repos.influxdata.com/influxdb.key | sudo apt-key add -
echo "deb https://repos.influxdata.com/debian stretch stable" | sudo tee /etc/apt/sources.list.d/influxdb.list