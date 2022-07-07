import io
import yaml

from fabric import Connection

PASSWORD = "animalflowerpot16candles"

hosts = [
    # {"ip": "10.22.0.62", "name": "wildflower-tech-camera-5"},
    # {"ip": "10.22.0.30", "name": "wildflower-tech-camera-11"},
    # {"ip": "10.22.0.34", "name": "wildflower-tech-camera-2"},
    # {"ip": "10.22.0.38", "name": "wildflower-tech-camera-3"},
    # {"ip": "10.22.0.42", "name": "wildflower-tech-camera-4"},
    # {"ip": "10.22.0.14", "name": "wildflower-tech-camera-6"},
    # {"ip": "10.22.0.46", "name": "wildflower-tech-camera-7"},
    # {"ip": "10.22.0.50", "name": "wildflower-tech-camera-8"},
    {"ip": "192.168.0.111"},
    {"ip": "192.168.0.115"},
    {"ip": "192.168.0.120"},
    {"ip": "192.168.0.114"},
    {"ip": "192.168.0.118"},
    {"ip": "192.168.0.113"},
    {"ip": "192.168.0.117"},
    {"ip": "192.168.0.116"},
    {"ip": "192.168.0.119"},
    {"ip": "192.168.0.112"},
]

environment = "724fe65b-f925-48a1-9ae0-ee1b85443d64"

details = {
  "wildflower-tech-zero-1": {
    "assignment_id": "ad2c173e-f3e1-4982-9450-3c1b8cd56f43",
    "device_id": "de796bd8-c4db-4658-8a64-e83fbaf641b3"
  },
  "wildflower-tech-zero-2": {
    "assignment_id": "63b92e03-8159-44be-98a9-a4b0dd42ebfa",
    "device_id": "897d5bb7-1596-40b3-9e30-ec012c558a0b"
  },
  "wildflower-tech-zero-3": {
    "assignment_id": "bce314b7-eb43-4725-9887-66d011f531df",
    "device_id": "feb43c3b-8f6f-4fdf-a81e-080425b6542e"
  },
  "wildflower-tech-zero-4": {
    "assignment_id": "9bef51b7-1141-44c1-9ac5-f51ff787ae34",
    "device_id": "affcf42f-8d4e-40a7-b9fc-57df4f7ff408"
  },
  "wildflower-tech-zero-5": {
    "assignment_id": "da779a22-4f7f-40d9-9bbb-1ae3d8befc1f",
    "device_id": "974741f8-7b91-415b-8d51-be237526f241"
  },
  "wildflower-tech-zero-6": {
    "assignment_id": "468d6091-8856-4eae-aaf5-71d582e9344c",
    "device_id": "0f7b36de-8b49-4f2b-aaed-9946cdb9ea6a"
  },
  "wildflower-tech-zero-7": {
    "assignment_id": "d70e577d-447c-4f15-ad87-1e561efa59da",
    "device_id": "35541c73-a747-469c-a1f4-f8e2a731eb54"
  },
  "wildflower-tech-zero-8": {
    "assignment_id": "df9aa4f7-f42b-4457-abcb-f7cf123a17a9",
    "device_id": "f78699f4-1846-41b3-bb63-26730dd9a303"
  },
  "wildflower-tech-zero-9": {
    "assignment_id": "91a3c159-0d13-430d-8a24-9a585641d1cf",
    "device_id": "abcda1a4-2192-41a5-ac66-a94ba312b864"
  },
  "wildflower-tech-zero-10": {
    "assignment_id": "784908e3-965e-483d-851f-ea86b57cfdfe",
    "device_id": "47d4aa08-6eef-4c1a-a596-9e87064e20ad"
  }
}
for host in hosts:
    try:
        c = Connection(host["ip"], user="wildflowertech", connect_kwargs={
            "password": PASSWORD,
        })
        print("=" * 90)
        print("starting %s" % host['ip'])
        print("=" * 90)
        # c.sudo("pip install yq", password=PASSWORD, warn=True, hide='both')
        # c.run("cat /boot/wildflower-config.yml | yq -r '.[\"environment-id\"]'", hide='both')

        c.sudo("apt-get install build-essential tk-dev libncurses5-dev libncursesw5-dev libreadline6-dev libdb5.3-dev libgdbm-dev libsqlite3-dev libssl-dev libbz2-dev libexpat1-dev liblzma-dev zlib1g-dev libffi-dev -y", password=PASSWORD, warn=True, hide="stdout")
        # c.sudo("wget https://www.python.org/ftp/python/3.7.2/Python-3.7.2.tar.xz && tar xf Python-3.7.2.tar.xz && cd Python-3.7.2 && ./configure && make -j 4 && sudo make altinstall", password=PASSWORD, warn=True, hide="stdout")
        c.run("cd Python-3.7.2 && ./configure --enable-optimizations && make -j")
        c.sudo("cd Python-3.7.2 && make altinstall", password=PASSWORD, warn=True)

        c.put('mac_addresses.txt', 'mac_addresses.txt')
        current_hostname = c.run('hostname', hide='both').stdout.strip()
        hostname = c.run('cat /boot/wildflower-config.yml | yq -r .hostname', hide='both').stdout.strip()
        print(hostname)
        if hostname != current_hostname:
            print("=" * 90)
            print("resetting hostname")
            print("=" * 90)
            c.sudo("hostname $( cat /boot/wildflower-config.yml | yq -r .hostname)", password=PASSWORD, warn=True, hide='both')
            c.sudo(f"sed 's/{current_hostname}/{hostname}/g' /etc/hosts", password=PASSWORD, warn=True, hide='both')

        info = details[hostname]
        f = io.StringIO()
        yaml.dump({
                  "hostname": hostname,
                  "device_id": info["device_id"],
                  "environment-id": environment,
                  "assignment-id": info["assignment_id"]
                  }, f)
        f.seek(0)
        c.put(f, "wildflower-config.yml")
        c.sudo("chown root:root wildflower-config.yml", password=PASSWORD, hide="both")
        c.sudo("mv wildflower-config.yml /boot/wildflower-config.yml", password=PASSWORD, hide="both")
        c.run("cat /boot/wildflower-config.yml")
        c.put("../shoe_sensor/collect_honeycomb.py", "collect_honeycomb.py")
        c.put("../shoe_sensor/run.sh", "run.sh")
        c.sudo("chown root:root collect_honeycomb.py", password=PASSWORD, hide="both")
        c.sudo("mv collect_honeycomb.py shoes/collect_honeycomb.py", password=PASSWORD, hide="both")
        c.sudo("chown root:root run.sh", password=PASSWORD, hide="both")
        c.sudo("mv run.sh shoes/run.sh", password=PASSWORD, hide="both")


        c.sudo('systemctl restart  wf-shoe.service', password=PASSWORD, warn=True)

        # c.sudo('reboot', password=PASSWORD, warn=True)
        # print(c.run("k3s --version").stdout)
        # c.put('k3s-config.json', 'k3s-config.json')
        # c.sudo('mv k3s-config.json /usr/lib/wildflower/broadcast/k3s-config.json', password=PASSWORD, warn=True)
        # c.sudo('systemctl stop k3s', password=PASSWORD, warn=True)
        # c.sudo('apt -o Acquire::ForceIPv4=true update', password=PASSWORD, warn=True)
        # c.sudo('apt -o Acquire::ForceIPv4=true upgrade -y', password=PASSWORD, warn=True)
        # c.sudo('rm /usr/local/bin/k3s*', password=PASSWORD, warn=True)
        # c.sudo('rm -rf /var/lib/rancher/k3s/data/*', password=PASSWORD, warn=True)
        # c.sudo('curl -sfL https://get.k3s.io -o install_k3s.sh', password=PASSWORD, warn=True)
        # c.sudo('sh install_k3s.sh', password=PASSWORD, warn=True)
        # c.put('k3s-agent.service', 'k3s.service')
        # c.sudo('chown root:root k3s.service', password=PASSWORD, warn=True)
        # c.sudo('chmod 555 k3s.service', password=PASSWORD, warn=True)
        # c.sudo('systemctl stop k3s', password=PASSWORD, warn=True)
        # c.sudo('mv k3s.service /etc/systemd/system/k3s.service', password=PASSWORD, warn=True)
        # c.sudo('systemctl daemon-reload', password=PASSWORD, warn=True)
        # c.sudo('systemctl enable k3s', password=PASSWORD, warn=True)
        # c.sudo('systemctl restart k3s', password=PASSWORD, warn=True)
        # print(c.run("k3s --version").stdout)
        # c.sudo('reboot', password=PASSWORD, warn=True)
        # c.sudo('mkdir -p /data', password=PASSWORD)
    except Exception as e:
        print(e)
        pass
