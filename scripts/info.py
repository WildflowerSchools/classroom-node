from fabric import Connection


PASSWORD = "animalflowerpot16candles"

hosts = [
    {"ip": "10.217.71.132"},
    {"ip": "10.217.71.126"},
    {"ip": "10.217.71.127"},
    {"ip": "10.217.71.134"},
    {"ip": "10.217.71.129"},
    {"ip": "10.217.71.133"},
]


for host in hosts:
    try:
        c = Connection(host["ip"], user="wildflowertech", connect_kwargs={
            "password": PASSWORD,
        }, connect_timeout=30)
        print("starting %s" % host['ip'])
        hostname = c.run("cat /boot/wildflower-config.yml | yq -r .hostname").stdout.strip()
        print(hostname)
        c.sudo(f'chown -R wildflowertech:wildflowertech shoes/', password=PASSWORD)
        c.sudo(f'chmod -R 775 shoes', password=PASSWORD)
        c.run("ls -al shoes")
        shoe_list = c.run("ls shoes | grep measurement_data").stdout
        shoe_list = shoe_list.split()
        print(shoe_list)
        for csv_name in shoe_list:
            c.get(f'shoes/{csv_name}', local=f'shoe-data/{hostname}-{csv_name}')
        c.sudo('shutdown 0', password=PASSWORD)
    except Exception:
        print("fail")
        pass
